from A3CAgent import A3CAgent
from env.DecoderEnv import DecoderEnv
from Config import Config

decoder_model_path = '/home/naposto/phd/nokia/digital_twin/models/ce_na_na_wo_clip'
tbs_table_path    = '/home/naposto/phd/generate_lte_tbs_table/samples/cpp_tbs.json'

beta_low = (1, 50)
beta_medium = (50, 650)
beta_high = (650, 700)
beta_all = (1, 700)

noise_low = (-15,50)
noise_medium = (50,80)
noise_high = (80, 100)
noise_all = (10, 100)

decoder_env = DecoderEnv(
    decoder_model_path = decoder_model_path,
    tbs_table_path     = tbs_table_path,
    noise_range        = noise_high,
    beta_range         = beta_high
)

config = Config()
config.seed = 1
config.environment = decoder_env
config.num_episodes_to_run = 2e3
config.randomise_random_seed = False
config.runs_per_agent = 3
config.save_results = True
config.save_weights = True
config.load_initial_weights = False
config.save_weights_period = 1e3
config.hyperparameters = {
    'Actor_Critic_Common': {
        'learning_rate': 1e-4,
        'discount_rate': 0.99,
        'linear_hidden_units': [5, 32, 64, 100],
        'num_actor_outputs': 1,
        'final_layer_activation': ['softmax', 'softmax', None],
        'normalise_rewards': False,
        'add_extra_noise': False,
        'tau': 0.005,
        'batch_size': 64,
        'include_entropy_term': True,
        'local_update_period': 1, # in episodes
        'entropy_beta': 0.1,
        'entropy_contrib_prob': 1,
        'Actor': {
            'linear_hidden_units': [100, 40]
        },
        'Critic': {
            'linear_hidden_units': [16, 4]
        }
    },
        
}

# entropy_betas = [0.1, 0.01, 0.5]
entropy_betas = [0.1,0.2,  .05, 1]

import copy
for beta_range, beta in zip([beta_high], ['high']):
    for noise_range, noise in zip([noise_low], ['low']):
        decoder_env = DecoderEnv(
            decoder_model_path = decoder_model_path,
            tbs_table_path = tbs_table_path,
            noise_range = noise_range, 
            beta_range= beta_range,
            policy_output_format = 'mcs_prb_joint'
        )
        for entropy_beta in entropy_betas:
            for run_idx in range(config.runs_per_agent):
                seed = run_idx * 32 + 1
                config = copy.deepcopy(config)
                config.seed = seed
                config.environment = decoder_env
                config.hyperparameters['Actor_Critic_Common']['entropy_beta'] = entropy_beta
                save_folder = '/home/naposto/phd/nokia/data/csv_45/low_noise_high_beta_joint/run_{}_beta_{}_noise_{}_entropy_{}.csv'
                config.results_file_path = save_folder.format(run_idx, beta, noise, entropy_beta)
                config.save_weights = True
                config.save_weights_file = '/home/naposto/phd/nokia/data/csv_45/low_noise_high_beta_joint/run_{}_beta_{}_noise_{}_entropy_{}.h5'.format(run_idx, beta, noise, entropy_beta)
                A3C_Agent = A3CAgent(config, 8)
                A3C_Agent.run_n_episodes()