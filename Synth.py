# A file to play programatically created audio with the keyboard
import numpy as np
import pyaudio
import tkinter as tk
import os
import time
import matplotlib.pyplot as plt
from scipy import signal

# TODO: Try a class-based system
# TODO: Shift and capslock currently only work if chord buttons are pressed down. Due to using keysym as identifier. Use keycodes
# TODO: Fix crackling when user presses a second key

os.system('xset r off')

BITRATE = 16000     #number of frames per second/frameset.      
BUFFER_LENGTH = 0.02  # Length of buffer in seconds
BUFFER_FRAMES_NR = int(BITRATE*BUFFER_LENGTH)
ET_RATIO = 2**(1/12)  # Semitone ratio for equal temperament

# Dictionaries for key presses. Should use key codes instead of key symbols since capslock changes symbol. Should be set programatically
key_dict_scale = {"1":0,"2":1,"3":2,"4":3,"5":4,"6":5,"7":6,"8":7}
key_dict_chord = {"j":0,"i":1,"k":2,"o":3,"l":4,"p":5,"oslash":6,"aring":7,"ae":8}
key_dict_misc = {"f":0,"g":1,"Shift_L":2,"Caps_Lock":3}


# Setting up dictionaries with correct keycodes -------------------------
counter = 0
keycodes = []
values = []

def get_keycode(event):
    global keycodes
    keycodes.append(event.keycode)

def standard_settings():
    global keycodes
    global values
    global key_dict_scale
    global key_dict_chord
    global key_dict_misc

    for key in key_dict_scale.keys():
        values.append(key_dict_scale[key])
        temp.event_generate(f"<Key-{key}>")
    key_dict_scale = dict(zip(keycodes, values))
    keycodes = []
    values = []
    for key in key_dict_chord.keys():
        values.append(key_dict_chord[key])
        temp.event_generate(f"<Key-{key}>")
    key_dict_chord = dict(zip(keycodes, values))
    keycodes = []
    values = []
    for key in key_dict_misc.keys():
        values.append(key_dict_misc[key])
        temp.event_generate(f"<Key-{key}>")
    key_dict_misc = dict(zip(keycodes, values))
    temp.destroy()

temp = tk.Tk()
temp.minsize(width=200, height=200)
temp.title("Settings")
temp.configure(bg="black", width=500, height=500)
temp.bind("<Key>", get_keycode)
button_1 = tk.Button(temp, height=1, width=10, text="Standard keys", bg="blue", fg="white", command=standard_settings)
button_2 = tk.Button(temp, height=1, width=10, text="Custom keys", bg="blue", fg="white",  command=temp.destroy)
button_1.pack(pady=30)
button_2.pack()
temp.mainloop()

# ^ Setting up dictionaries with correct keycodes ---------------------------

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
    alt_scale = np.copy(minor_scale)

    scale = np.copy(default_scale)
    scale_degree = 0

    active_freqs = np.zeros(9)  #np.zeros((5,1))
    just_pressed = np.zeros(9)  #np.zeros((5,1))
    just_released = np.zeros(9)  #np.zeros((5,1))
    ramp_up = np.linspace(0, 1, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile((5,1))
    ramp_down = np.linspace(1, 0, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

    t = np.linspace(0, BUFFER_LENGTH, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

    no_sound = np.zeros(BUFFER_FRAMES_NR, dtype=np.float32)
    #no_sound_a = np.tile(no_sound, (5,1))
    data = no_sound

    save_data_0 = np.empty(BUFFER_FRAMES_NR)
    save_data_1 = np.empty(BUFFER_FRAMES_NR)
    mixed_flag = False
    count = 0

    def array_mixing():
        # TODO: Use numpy for mixing to speed up
        # Causes clipping for some reason
        #data_array = np.copy(no_sound_a)
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
                if f < 10:
                    continue
                phase = f*BUFFER_LENGTH*count%(2*np.pi)
                rel_intensity = f/base_freq  # In order for all notes to play at same decibel
                if just_pressed[i]:
                    temp_data += np.sin(f*t + phase)*ramp_up/rel_intensity
                    just_pressed[i] = 0
                elif just_released[i]:
                    temp_data += np.sin(f*t + phase)*ramp_down/rel_intensity
                    just_released[i] = 0
                    active_freqs[i] = 0
                else:
                    temp_data += np.sin(f*t + phase)/rel_intensity
            scaling_factor = max(1, np.sum(active_freqs > 10))  # Number of "oscillators", min 1
            temp_data = 0.8*temp_data/scaling_factor
            if temp_data[100] > 0.5:
                save_data_0 = np.copy(save_data_1)
                save_data_1 = np.copy(temp_data)
            data = temp_data.astype(np.float32).tobytes()
            #end = time.perf_counter()
            #print(f"mixed at {end:.5f} \n")


    def callback(in_data, frame_count, time_info, status):
        global data
        global mixed_flag
        global count

        return_data = np.copy(data)
        mixed_flag = False
        count += 1
        return (return_data, pyaudio.paContinue)

    def set_chord_freqs(degree):
        global scale
        freqs = scale[degree : degree+9]
        return freqs

    def key_down(event):
        global active_freqs
        global just_pressed
        global just_released
        global scale
        global alt_scale
        global major_scale
        global flat_scale
        global sharp_scale
        global scale_degree
        global chord_freqs
        # TODO: Add button for sharp and flat notes. Half done. not quite working smoothly
        # TODO: Change to switch-case?
        # Script does not enter this function when pressing 4 or 8 with 3+ chord tones playing
        # Holding shift changes key symbol, thus minor is not working

        key = event.keycode
        if key in key_dict_chord:
            index = key_dict_chord[key]
            active_freqs[index] = chord_freqs[index]
            just_pressed[index] = 1
        else:
            if key in key_dict_scale:
                scale_degree = key_dict_scale[key]
            elif key in key_dict_misc:
                action = key_dict_misc[key]
                if action == 0:
                    scale = scale/ET_RATIO
                elif action == 1:
                    scale = scale*ET_RATIO
                elif action == 2 or action == 3:
                    scale, alt_scale = alt_scale, scale
            chord_freqs = set_chord_freqs(scale_degree)
            active_freqs = chord_freqs*(active_freqs > 10)


    def key_up(event):
        global active_freqs
        global just_released
        global scale
        global alt_scale
        global major_scale
        global scale_degree
        global active_freqs
        global chord_freqs

        key = event.keycode
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
                scale, alt_scale = alt_scale, scale
            chord_freqs = set_chord_freqs(scale_degree)
            active_freqs = chord_freqs*(active_freqs > 10)


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
    mixing()
    root.mainloop()
    stream.stop_stream()
    stream.close()
    p.terminate()
    #plt.plot(t,save_data_0,'r',t,save_data_1,'b')
    #plt.show()
    os.system('xset r on')
except:
    print("something went wrong")
    os.system('xset r on')
