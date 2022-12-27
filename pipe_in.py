from sys import byteorder
from common_utils import MODE_INFERENCE, MODE_SCHEDULING_AC, MODE_SCHEDULING_NO, MODE_SCHEDULING_RANDOM, MODE_TRAINING
from env.SrsRanEnv import SrsRanEnv
import multiprocessing as mp
from Config import Config
from A3CAgent import A3CAgent
from multiprocessing import shared_memory
import numpy as np


ACTOR_IN = '/tmp/actor_in'
ACTOR_OUT = '/tmp/actor_out'
VERIFY_ACTION = '/tmp/verify_action'
REWARD_IN = '/tmp/return_in'

class Coordinator():
    def __init__(self):
        self.total_agents = 8
        self.verbose = 0
        self.scheduling_mode = MODE_SCHEDULING_AC
        self.training_mode   = MODE_TRAINING

        # validity byte
        # observation is: snr, beta, bsr all are integers32
        if (self.in_scheduling_mode()):
            try:
                shm_observation = shared_memory.SharedMemory(create = True,  name = 'observation', size = (16) * self.total_agents)
            except Exception:
                shm_observation = shared_memory.SharedMemory(create = False, name = 'observation', size = (16) * self.total_agents)

            nd_array = np.ndarray(shape=(4 * self.total_agents), dtype=np.int32, buffer=shm_observation.buf)
            nd_array[:] = np.full(shape=(4 * self.total_agents), fill_value=0)

            try:
                shm_action = shared_memory.SharedMemory(create = True,  name = 'action', size = (12) * self.total_agents)
            except Exception:
                shm_action = shared_memory.SharedMemory(create = False, name = 'action', size = (12) * self.total_agents)

            nd_array = np.ndarray(shape=(3 * self.total_agents), dtype=np.int32, buffer=shm_action.buf)
            nd_array[:] = np.full(shape=(3 * self.total_agents), fill_value=0)

            try:
                shm_verify_action = shared_memory.SharedMemory(create = True,  name = 'verify_action', size = (8) * self.total_agents)
            except Exception:
                shm_verify_action = shared_memory.SharedMemory(create = False, name = 'verify_action', size = (8) * self.total_agents)

            nd_array = np.ndarray(shape=(2 * self.total_agents), dtype=np.int32, buffer=shm_verify_action.buf)
            nd_array[:] = np.full(shape=(2 * self.total_agents), fill_value=0)

        try:
            shm_reward = shared_memory.SharedMemory(create = True,  name = 'result', size = (28) * self.total_agents)
        except Exception:
            shm_reward = shared_memory.SharedMemory(create = False, name = 'result', size = (28) * self.total_agents)    

        nd_array = np.ndarray(shape=(7 * self.total_agents), dtype=np.int32, buffer=shm_reward.buf)
        nd_array[:] = np.full(shape=(7 * self.total_agents), fill_value=0)                

        self.config = self.get_environment_config()
        self.processes_started_successfully = mp.Value('i', 0)
        
        self.a3c_agent = A3CAgent(
            self.config, 
            self.total_agents, 
            scheduling_mode=self.scheduling_mode,
            training_mode=self.training_mode
        )

        if (self.in_scheduling_mode()):
            self.sched_proc = mp.Process(target=self.rcv_obs_send_act_func, name= 'scheduler_intf')
        else:
            self.sched_proc = None
        
        self.decod_proc = mp.Process(target=self.rcv_return_func, name='decoder_intf')

        if (self.in_scheduling_mode):
            self.cond_observations = [mp.Condition() for _ in range(self.total_agents)]
            self.cond_actions      = [mp.Condition() for _ in range(self.total_agents)]
            self.cond_verify_action= [mp.Condition() for _ in range(self.total_agents)]
        self.cond_rewards      = [mp.Condition() for _ in range(self.total_agents)]

    def kill_all(self):
        print('Killing coordinator')
        self.a3c_agent.kill_all()
        if (self.decod_proc.is_alive()):
            self.decod_proc.kill()
            self.decod_proc.join()
        if (self.sched_proc.is_alive()):
            self.sched_proc.kill()
            self.sched_proc.join()

    def get_environment_config(self) -> Config:
        import sys
        args = sys.argv[1:]
        if (len(args) >= 4):
            seed = int(args[0])
            num_episodes = int(args[1])
            results_file = args[2]
            load_pretrained_weights = bool(int(args[3]))
            if (load_pretrained_weights):
                pretrained_weights_path = args[4]
        else:
            i = 0
            seed = i * 35
            num_episodes = 10000
            # results_file = '/home/naposto/phd/nokia/data/csv_47/real_enb_wo_pretrained_agent_2/run_0.csv'
            results_file = '/home/naposto/phd/nokia/experiment_mcs_policy/results.csv'
            load_pretrained_weights = False
            # actor_pretrained_weights_path = '/home/naposto/phd/nokia/pretraining/colab_weights_qac/q_actor_weights_1users.h5'
            actor_pretrained_weights_path = '/home/naposto/phd/nokia/infocom/models/own_scheduler/cpu_very_high__inference__actor.h5'            
            critic_pretrained_weights_path = '/home/naposto/phd/nokia/infocom/models/own_scheduler/cpu_very_high__inference__critic.h5'



        # index 0 -> initial seed
        # index 1 -> number of episodes
        # index 2 -> results file
        # index 3 -> agent's initial weight [True | False]
        # index 4 -> agent's initial weight file (in .h5 format)

        config = Config()
        config.seed = seed
        config.environment = SrsRanEnv(
            title = 'SRS RAN Environment', verbose=self.verbose, penalty = 5, 
            input_dims = 2, 
            scheduling_mode=self.scheduling_mode)
        config.num_episodes_to_run = 5e4
        config.num_episodes_inference = 1e4
        config.save_results = True
        config.results_file_path = results_file
        # config.results_file_path = '/home/naposto/phd/nokia/data/csv_46/real_enb_high_beta_low_snr_trained_2.csv'

        config.save_weights = True
        config.save_weights_period = 100
        config.save_weights_file = '/home/naposto/phd/nokia/experiment_mcs_policy/'
        
        config.load_initial_weights = load_pretrained_weights
        if (config.load_initial_weights):
            config.initial_weights_path = actor_pretrained_weights_path
            config.critic_initial_weights_path = critic_pretrained_weights_path

        config.hyperparameters = {
            'Actor_Critic_Common': {
                'learning_rate': 1e-4,
                'clipping': False,
                'use_state_value_critic': False,
                'batch_size': 64,
                'local_update_period': 1,
                'include_entropy_term': True,
                'entropy_contribution': 0
            },
        }

        return config

    def in_scheduling_mode(self):
        return self.scheduling_mode == MODE_SCHEDULING_AC or self.scheduling_mode == MODE_SCHEDULING_RANDOM

    def start(self):
        if (self.in_scheduling_mode()):
            self.sched_proc.start()
        self.decod_proc.start()
        inputs = []
        for idx in range(self.total_agents):
            input = {
                'cond_reward': self.cond_rewards[idx]
            }
            if (self.in_scheduling_mode()):
                input['cond_observation'] = self.cond_observations[idx]
                input['cond_action']      = self.cond_actions[idx]
                input['cond_verify_action']     = self.cond_verify_action[idx]
            inputs.append(input)
        self.a3c_agent.run_n_episodes(self.processes_started_successfully, inputs)
        if (self.in_scheduling_mode()):
            self.sched_proc.join()
        self.decod_proc.join()

    def get_action(self):
        return 

    def rcv_return_func(self):
        shm_reward = shared_memory.SharedMemory(create = False,  name = 'result')
        self.reward_nd_array = np.ndarray(
            shape=(7 * self.total_agents),
            dtype= np.int32,
            buffer = shm_reward.buf
        )
        while (self.processes_started_successfully.value == 0):
            pass
        print('Receive result thread waiting for all processes to start...OK')
        is_file_open = False
        while (not is_file_open):
            try:
                with open(REWARD_IN, mode='rb') as file_read:
                    is_file_open = True
                    print('Opening receive reward socket...')
                    while (True):
                        content = file_read.read(24)
                        if (len(content) <= 0):
                            print('EOF')
                            break
                        tti = int.from_bytes(content[0:2], "little")
                        rnti = int.from_bytes(content[2:4], "little")
                        dec_time = int.from_bytes(content[4:8], "little")
                        crc = int.from_bytes(content[8:9], "little")
                        dec_bits = int.from_bytes(content[12:16], "little")
                        mcs      = int.from_bytes(content[16:18], "little")
                        prb      = int.from_bytes(content[18:20], "little")
                        snr      = int.from_bytes(content[20:24], "little")

                        result_buffer = np.array([tti, crc, dec_time, dec_bits, mcs, prb, snr], dtype = np.int32)
                        agent_idx = tti % self.total_agents
                        if (self.verbose == 1):
                            print('Res {} - {}'.format(agent_idx, result_buffer))
                        cond_reward = self.cond_rewards[agent_idx]
                        result_buffer[0] = 1
                        with cond_reward:
                            self.reward_nd_array[agent_idx * 7: (agent_idx + 1) * 7] = result_buffer
                            cond_reward.notify()
            except FileNotFoundError as e:
                pass
                


    def rcv_obs_send_act_func(self):
        shm_observation = shared_memory.SharedMemory(create = False,  name = 'observation')
        shm_action = shared_memory.SharedMemory(create = False,  name = 'action')
        shm_verify_action = shared_memory.SharedMemory(create = False, name = 'verify_action')

        self.observation_nd_array = np.ndarray(
            shape=(4 * self.total_agents), 
            dtype= np.int32, 
            buffer = shm_observation.buf)

        
        self.action_nd_array = np.ndarray(
            shape=(3 * self.total_agents),
            dtype= np.int32,
            buffer = shm_action.buf
        )

        self.verify_action_nd_array = np.ndarray(
            shape=(2 * self.total_agents),
            dtype= np.int32,
            buffer = shm_verify_action.buf
        )

        while (self.processes_started_successfully.value == 0):
            pass
        print('Receive obs thread waiting for all processes to start... OK')
        is_actor_in_open = False
        while (not is_actor_in_open):
            try:                
                with open(ACTOR_IN, mode='rb') as file_read:
                    is_actor_in_open = True
                    is_verify_action_open = False
                    while (not is_verify_action_open):
                        try:
                            with open(VERIFY_ACTION, mode = 'rb') as verify_action_fd:
                                is_verify_action_open = True
                                with open(ACTOR_OUT,  mode='wb') as file_write:
                                    print('Opening receive state socket...')
                                    while (True):
                                        content = file_read.read(16)
                                        if (len(content) <= 0):
                                            print('EOF')
                                            break
                                        tti  = int.from_bytes(content[0:2], "little")
                                        rnti = int.from_bytes(content[2:4], "little")
                                        bsr =  int.from_bytes(content[4:8], "little")
                                        snr =  int.from_bytes(content[8:12], "little", signed = True)
                                        beta = int.from_bytes(content[12:], "little")
                                        
                                        agent_idx = tti % self.total_agents
                                        observation = np.array([tti, beta, snr, bsr], dtype = np.int32)
                                        if (self.verbose == 1):
                                            print('Obs {} - {}'.format(agent_idx, observation))
                                        cond_observation   = self.cond_observations[agent_idx]
                                        cond_action        = self.cond_actions[agent_idx]
                                        cond_verify_action = self.cond_verify_action[agent_idx]
                                        observation[0] = 1
                                        with cond_observation:
                                            self.observation_nd_array[agent_idx * 4: (agent_idx + 1) * 4] = observation
                                            cond_observation.notify()

                                        with cond_action:
                                            while self.action_nd_array[agent_idx * 3]  == 0:
                                                cond_action.wait(0.001)

                                        self.action_nd_array[agent_idx * 3 ] = 0
                                        mcs, prb = self.action_nd_array[agent_idx * 3 + 1].item(), self.action_nd_array[agent_idx * 3 + 2].item()
                                        if (self.verbose == 1):
                                            print('Act {} - {}'.format(agent_idx, [tti, mcs, prb]))

                                        action_mcs = mcs.to_bytes(1, byteorder="little")
                                        action_prb = prb.to_bytes(1, byteorder="little")
                                        ext_byte_arr = action_mcs +  action_prb
                                        file_write.write(ext_byte_arr)
                                        file_write.flush()

                                        verify_action_content = verify_action_fd.read(4)
                                        if (len(verify_action_content) < 0):
                                            print('EOF')
                                            break
                                        action_verified = int.from_bytes(verify_action_content[0: 4], "little")
                                        with cond_verify_action:
                                            self.verify_action_nd_array[agent_idx * 2: (agent_idx + 1) * 2] = np.array([1, action_verified], dtype = np.int32)
                                            cond_verify_action.notify()
                        except FileNotFoundError as e:
                            if (is_actor_in_open and is_verify_action_open):
                                raise e
                            pass
            except FileNotFoundError as e:
                if (is_actor_in_open):
                    raise e
                pass


def exit_gracefully():
    coordinator.kill_all()


coordinator = None

if __name__== '__main__':
    import signal
    signal.signal(signal.SIGINT , exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    coordinator = Coordinator()
    coordinator.start()

