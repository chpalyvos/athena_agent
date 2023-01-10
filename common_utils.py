import numpy as np
from multiprocessing import shared_memory


MODE_SCHEDULING_NO = 0
MODE_SCHEDULING_AC = 1
MODE_SCHEDULING_RANDOM = 2

MODE_TRAINING = 1
MODE_INFERENCE = 0

NOISE_MIN = -15.0
NOISE_MAX = 100.0
BETA_MIN  = 1.0
BETA_MAX  = 1000.0
BSR_MIN   = 0
BSR_MAX   = 180e3

def import_tensorflow(debug_level: str, import_tfp = False):
    import os
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'    
    import tensorflow as tf

    tfp = None
    if (import_tfp):
        import tensorflow_probability as tfp
    return tf, os, tfp

def get_shared_memory_ref(
        size, dtype, share_memory_name):
        total_variables = int( size / dtype.itemsize )
        shm = shared_memory.SharedMemory(name=share_memory_name, create=False, size=size)        
        shared_weights_array = np.ndarray(
                                shape = (total_variables, ),
                                dtype = dtype,
                                buffer = shm.buf)
        return shm, shared_weights_array

def map_weights_to_shared_memory_buffer(weights, shared_memory_buf):
        buffer_idx = 0
        for idx_weight in range(len(weights)):
            weight_i = weights[idx_weight]
            shape = weight_i.shape
            size  = weight_i.size
            weights[idx_weight] = np.ndarray(shape = shape,
                                           dtype = weight_i.dtype,
                                           buffer = shared_memory_buf[buffer_idx: (buffer_idx + size)])
            buffer_idx += size

        return weights

def publish_weights_to_shared_memory(weights, shared_ndarray):
        buffer_idx = 0
        for weight in weights:
            flattened = weight.flatten().tolist()
            size = len(flattened)
            shared_ndarray[buffer_idx: (buffer_idx + size)] = flattened
            buffer_idx += size

def save_weights(model, save_weights_file, throw_exception_if_error = False):
    try:
        print('Saving weights to {} ...'.format(save_weights_file), end='')
        model.save_weights(save_weights_file)
        print('Success')
    except Exception as e:
        print('Error' + str(e))
        if (throw_exception_if_error):
            raise e    

def get_basic_actor_network(tf, tfp, num_states):
    keras = tf.keras
    layers = keras.layers

    state_input = keras.Input(shape = (num_states))
    x = layers.Dense(16, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (state_input)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    
    norm_params = layers.Dense(1, kernel_initializer = keras.initializers.HeNormal())(x)
    actor = keras.Model(state_input, norm_params)
    return actor

def get_basic_critic_network(tf, num_states, num_actions):
    keras = tf.keras
    layers = keras.layers
    state_input = keras.Input(shape = (num_states))
    action_input = keras.Input(shape = (num_actions))
    x = layers.Concatenate()([state_input, action_input])
    x = layers.Dense(16, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    x = layers.Dense(128, activation = 'relu', kernel_initializer = keras.initializers.HeNormal()) (x)
    q = layers.Dense(1, kernel_initializer = keras.initializers.HeNormal()) (x)
    critic = keras.Model(inputs = [state_input, action_input], outputs=q)
    return critic

cpu_min = 0
snr_min = 11
cpu_max = 1000
snr_max = 30
def normalize_state(state):
    # cpu, snr1
    state = state.copy()
    state[0] -= cpu_min
    state[0] /= (cpu_max - cpu_min)
    state[1] -= snr_min
    state[1] /= (snr_max - snr_min)
    return state

def denormalize_state(state):
    state = state.copy()
    state[0] = state[0] * (cpu_max - cpu_min) + cpu_min
    state[1] = state[1] * (snr_max - snr_min) + snr_min
    return state

tbs_max = 24496
tbs_min = 104
def normalize_tbsoutput(tbs):
    return (tbs - tbs_min) / (tbs_max - tbs_min)

def denormalize_tbs(tbsoutput):
    return tbsoutput * (tbs_max - tbs_min) + tbs_min

if (__name__== '__main__'):
    tf, os, tfp = import_tensorflow('3', False)

    actor = get_basic_actor_network(tf, tfp, 2)
    actor.load_weights('/home/naposto/phd/nokia/pretraining/colab_weights_qac/q_actor_weights_1users.h5')
    critic = get_basic_critic_network(tf, 2, 1)
    critic.load_weights('/home/naposto/phd/nokia/pretraining/colab_weights_qac/v_critic_weights_1user.h5')
    state = np.array([1, 45], dtype = np.float32)
    action = np.array([0.5], dtype = np.float32)
    normalize_state(state)
    tf_state = tf.convert_to_tensor([state])
    tf_action = tf.convert_to_tensor([action])

    a = 1



    pass

    pass

    while (1):
        pass





