# A file to play programatically created audio with the keyboard
import tkinter as tk 
import numpy as np
import pyaudio
import os
import time
import matplotlib.pyplot as plt
from scipy import signal
from debouncer import Debouncer

# TODO: Debounce manually with a function. xset is linux only

# A BIG FAT COMMENT THAT'S NOT SUPPOSED TO BE IN MAIN BRANCH

os.system('xset r off')

BITRATE = 16000     #number of frames per second/frameset.      
BUFFER_LENGTH = 0.02  # Length of buffer in seconds
BUFFER_FRAMES_NR = int(BITRATE*BUFFER_LENGTH)
ET_RATIO = 2**(1/12)  # Semitone ratio for equal temperament

# Need to use keycodes instead of key symbols, since capslock modifies key symbols
# Should be set programatically
key_dict_scale = {"1":0,"2":1,"3":2,"4":3,"5":4,"6":5,"7":6,"8":7}
key_dict_chord = {"j":0,"k":1,"l":2,"oslash":3,"ae":4}
key_dict_misc = {"f":0,"g":1,"Shift_L":2,"Caps_Lock":3}

try:
    # Setting up tkinter
    root = tk.Tk()
    root.title("Kinda Synth")
    root.configure(bg="black")

    frame_1 = tk.Frame(root, height=200, width=200, bg="red")
    frame_1.pack()
    frame_2 = tk.Frame(root, height=200, width=200, bg="blue")
    frame_2.pack()

    #Setting up PyAudio
    PyAudio = pyaudio.PyAudio     #initialize pyaudio


    base_freq = 2*np.pi*261.63  # Angular frequencies for performance, this this by option
    semitones = np.empty(12)
    for i in range(12):
        semitones[i] = base_freq*ET_RATIO**i

    major_scale = np.copy(semitones[np.array([0,2,4,5,7,9,11])])
    major_scale = np.concatenate((major_scale, 2*major_scale, 4*major_scale))
    minor_scale = np.copy(semitones[np.array([0,2,3,5,7,8,10])])
    minor_scale = np.concatenate((minor_scale, 2*minor_scale, 4*minor_scale))
    """ 
    flat_maj_scale = major_scale/ET_RATIO
    sharp_maj_scale = major_scale*ET_RATIO
    flat_m_scale = minor_scale/ET_RATIO
    sharp_m_scale = minor_scale*ET_RATIO
    """

    default_scale = np.copy(major_scale)  #TODO: set this by an option

    scale = np.copy(default_scale)
    scale_degree = 0

    active_freqs = np.zeros(5)  #np.zeros((5,1))
    just_pressed = np.zeros(5)  #np.zeros((5,1))
    just_released = np.zeros(5)  #np.zeros((5,1))
    ramp_up = np.linspace(0, 1, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile((5,1))
    ramp_down = np.linspace(1, 0, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

    t = np.linspace(0, BUFFER_LENGTH, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

    no_sound = np.zeros(BUFFER_FRAMES_NR, dtype=np.float32)
    #no_sound_a = np.tile(no_sound, (5,1))
    data = no_sound

    save_data_0 = np.empty(BUFFER_FRAMES_NR)
    save_data_1 = np.empty(BUFFER_FRAMES_NR)
    count = 0
    mixed_flag = False

    def array_mixing():
        # TODO: Use numpy for mixing to speed up
        # Causes clipping for some reason
        phase = active_freqs*BUFFER_LENGTH*count
        ramp_array = just_pressed*ramp_up + just_released*ramp_down + 1
        data_array = np.sin(active_freqs*t + phase)*ramp_array
        data = np.sum(data_array, axis=0)
        active_freqs = active_freqs*(just_released != 1)
        just_released = np.zeros((5,1))


    def mixing():
        global data
        global just_pressed
        global just_released
        global count
        global no_sound
        global active_freqs
        global root
        global mixed_flag
        global save_data_0
        global save_data_1

        root.after(5, mixing)
        if mixed_flag:
            pass
        else:
            #start = time.perf_counter()
            #print(f"mixing at {start:.5f}")
            mixed_flag = True
            temp_data = np.copy(no_sound)
            for i, f in enumerate(active_freqs):
                phase = f*BUFFER_LENGTH*count%(2*np.pi)
                if just_pressed[i]:
                    temp_data += np.sin(f*t + phase)*ramp_up
                    just_pressed[i] = 0
                elif just_released[i]:
                    temp_data += np.sin(f*t + phase)*ramp_down
                    just_released[i] = 0
                    active_freqs[i] = 0
                else:
                    temp_data += np.sin(f*t + phase)
            max_amplitude = (np.amax(np.square(temp_data), initial=1))**0.5
            temp_data = 0.8*temp_data/max_amplitude
            if temp_data[100] > 0.5:
                save_data_0 = np.copy(save_data_1)
                save_data_1 = np.copy(temp_data)
            data = temp_data.astype(np.float32).tobytes()
            #end = time.perf_counter()
            #print(f"mixed at {end:.5f} \n")


    def callback(in_data, frame_count, time_info, status):
        global data
        global active_freqs
        global t
        global count
        global no_sound
        global just_pressed
        global just_released
        global ramp_up
        global ramp_down
        global mixed_flag
        # TODO: Mixing should be done while stream is playing, not after it has called callback
        # Note, if so the phase can not be determined in the mixing stage

        #call = time.perf_counter()
        #print(f"calling at {call:.5f} --------------------------------------------\n")
        #frame = data
        #return_data = frame.astype(np.float32).tobytes()
        return_data = data
        mixed_flag = False
        count += 1
        return (return_data, pyaudio.paContinue)

    def set_chord_freqs(degree):
        global scale
        freqs = np.empty(5)
        for i in range(5):
            freqs[i] = scale[degree + 2*i]
        return freqs

    def key_down(event):
        global data
        global active_freqs
        global just_pressed
        global just_released
        global scale
        global major_scale
        global flat_scale
        global sharp_scale
        global scale_degree
        global chord_freqs
        # TODO: Add button for sharp and flat notes. Half done. not quite working smoothly
        # TODO: Change to switch-case?
        # Script does not enter this function when pressing 4 or 8 with 3+ chord tones playing
        #    keycodes not working: 13, 17, 18, 31, 32

        key = event.keysym
        if key in key_dict_scale:
            # TODO: Make sure currently playing note changes. Half done. Clicks a little. 4 and 8 not always working
            scale_degree = key_dict_scale[key]
            chord_freqs = set_chord_freqs(scale_degree)
            active_freqs = chord_freqs*(active_freqs > 1)
        elif key in key_dict_chord:
            index = key_dict_chord[key]
            active_freqs[index] = chord_freqs[index]
            just_pressed[index] = 1
        elif key in key_dict_misc:
            action = key_dict_misc[key]
            if action == 0:
                scale = scale/ET_RATIO
            elif action == 1:
                scale = scale*ET_RATIO
            elif action == 2:
                # TODO: Use a better kind of comparison. This is not compatible with the way I'm doing sharps and flats
                if (scale == major_scale).all():
                    scale = minor_scale
                elif (scale == minor_scale).all():
                    scale = major_scale
            elif action == 3:
                if (scale == major_scale).all():
                    scale = minor_scale
                elif (scale == minor_scale).all():
                    scale = major_scale
            chord_freqs = set_chord_freqs(scale_degree)
            active_freqs = chord_freqs*(active_freqs > 1)

    def key_up(event):
        global data
        global active_freqs
        global just_pressed
        global just_released
        global scale
        global major_scale
        global scale_degree
        global active_freqs
        global chord_freqs
        
        key = event.keysym
        if key in key_dict_chord:
            index = key_dict_chord[key]
            just_released[index] = 1
        elif key in key_dict_misc:
            action = key_dict_misc[key]
            if action == 0:
                scale = scale*ET_RATIO
            elif action == 1:
                scale = scale/ET_RATIO
            elif action == 2:
                if (scale == major_scale).all():
                    scale = minor_scale
                elif (scale == minor_scale).all():
                    scale = major_scale
            chord_freqs = set_chord_freqs(scale_degree)
            active_freqs = chord_freqs*(active_freqs > 1)


    chord_freqs = set_chord_freqs(0)

    root.bind("<KeyPress>", key_down)
    root.bind("<KeyRelease>", key_up)

    p = PyAudio()
    stream = p.open(format=pyaudio.paFloat32, 
                    channels=1, 
                    rate=BITRATE, 
                    output=True,
                    stream_callback=callback,
                    frames_per_buffer=BUFFER_FRAMES_NR)

    #stream.start_stream()
    mixing()
    root.mainloop()
    stream.stop_stream()
    stream.close()
    p.terminate()
    plt.plot(t,save_data_0,'r',t,save_data_1,'b')
    plt.show()
    os.system('xset r on')
except:
    print("something went wrong")
    os.system('xset r on')
