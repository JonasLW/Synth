# A file to play programatically created audio with the keyboard
import numpy as np
import pyaudio
import tkinter as tk
import os
import time
import matplotlib.pyplot as plt
from scipy import signal
import tkinter.font as font

# TODO: Try a class-based system
# TODO: Add more interesting waveforms.
# TODO: Build ramp-up in to waveforms
# TODO: Add sustain function
# TODO: Add transpose function
# TODO: Add GUI
# TODO: Add custom keys functionality

os.system('xset r off')

BITRATE = 16000     #number of frames per second/frameset.      
BUFFER_LENGTH = 0.02  # Length of buffer in seconds
BUFFER_FRAMES_NR = int(BITRATE*BUFFER_LENGTH)
ET_RATIO = 2**(1/12)  # Semitone ratio for equal temperament

# Dictionaries for key presses.
key_dict_scale = {"1":0,"2":1,"3":2,"4":3,"5":4,"6":5,"7":6,"8":7}
# Extra chord tones for the sake of playing chord inversions.
# Note: System from d-h is opposite of system from j-ø to make inversions simpler. Consider making these fit the pattern of the ordinary chord tones instead
# Note that u and j presently give the same note (update: u has been disabled due to conflict with j)
key_dict_chord = {"d":0,"r":1,"f":2,"t":3,"g":4,"y":5,"h":6,
                  "j":7,"i":8,"k":9,"o":10,"l":11,"p":12,"oslash":13,
                  "aring":14,"ae":15} 
key_dict_misc = {"a":0,"s":1,"Shift_L":2,"Caps_Lock":3}
chord_symb_dict_maj = {0:"I maj7",1:"ii m7",2:"iii m7",3:"IV maj7",4:"V m7",5:"vi m7",6:"vii m7b5",7:"I maj7"}


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
button_2 = tk.Button(temp, height=1, width=10, text="Custom keys", bg="blue", fg="white",  command=standard_settings)
button_1.pack(pady=30)
button_2.pack()
temp.mainloop()

# ^ Setting up dictionaries with correct keycodes ---------------------------

#try:

#Setting up PyAudio
PyAudio = pyaudio.PyAudio     #initialize pyaudio


base_freq = 2*np.pi*130.81  # Angular frequencies for performance, this this by option
semitones = np.empty(12)
for i in range(12):
    semitones[i] = base_freq*ET_RATIO**i

major_scale = np.copy(semitones[np.array([0,2,4,5,7,9,11])])
major_scale = np.concatenate((major_scale, 2*major_scale, 4*major_scale, 8*major_scale))
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

active_freqs = np.zeros(16)  #np.zeros((5,1))
just_pressed = np.zeros(16)  #np.zeros((5,1))
just_released = np.zeros(16)  #np.zeros((5,1))
counters = np.zeros(16, dtype=np.int)
residual_freqs = np.zeros(16)
transition_flag = False
ramp_up = np.linspace(0, 1, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile((5,1))
ramp_down = np.linspace(1, 0, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

t = np.linspace(0, BUFFER_LENGTH, BUFFER_FRAMES_NR, endpoint=False, dtype=np.float32)  # tile(5,1)

no_sound = np.zeros(BUFFER_FRAMES_NR, dtype=np.float32)
#no_sound_a = np.tile(no_sound, (5,1))
data = no_sound

save_data_0 = np.zeros(BUFFER_FRAMES_NR)
save_data_1 = np.zeros(BUFFER_FRAMES_NR)
mixed_flag = False
scaling_factor = 1

def sinewave(f,t):
    fade_in = 1 - 1/(2*t/BUFFER_LENGTH + 1)
    return np.sin(f*t)

def sine_fade(f, t):
    fade_in = 1 - 1/(2*t/BUFFER_LENGTH + 1)  # Does not work as intended
    return np.sin(f*t)*0.5**(t/0.5)

def square(f, t):
    return signal.square(f*t)

def square_fade(f, t):
    return signal.square(f*t)*0.5**(t/0.5)

def saw(f, t):
    return signal.sawtooth(f*t)

def saw_fade(f, t):
    return signal.sawtooth(f*t)*0.5**(t/0.5)

def organ(f,t):
    return (0.1*np.sin(0.5*f*t)
            + np.sin(f*t)
            + 0.1*np.sin(3/2*f*t)
            + 0.05*np.sin(2*f*t)
            + 0.02*np.sin(8/3*f*t))/(0.1+1+0.1+0.05+0.02)

def organ_fade(f,t):
    return organ(f,t)*0.5**(t/0.5)

def square_sine(f, t):
    return (signal.square(f*t) + 0.3*np.sin(f*t))/1.3

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

def mixing(wave_cb):
    global data
    global just_pressed
    global just_released
    global counters
    global no_sound
    global active_freqs
    global root
    global mixed_flag
    global save_data_0
    global save_data_1
    global scaling_factor
    global transition_flag
    global residual_freqs

    root.after(5, mixing, wave_cb)
    if mixed_flag:
        pass
    else:
        mixed_flag = True
        temp_data = np.copy(no_sound)
        if transition_flag:
            for i, f in enumerate(residual_freqs):
                if f < 10:
                    continue
                time_passed = BUFFER_LENGTH*counters[i]
                #phase = f*time_passed%(2*np.pi)
                rel_intensity = np.sqrt(f/base_freq)  # In order for all notes to play at same decibel
                temp_data += wave_cb(f, t+time_passed)*ramp_down/rel_intensity
                residual_freqs[i] = 0
            transition_flag = False
            residual_freqs = np.zeros(16)

        for i, f in enumerate(active_freqs):
            if f < 10:
                counters[i] = 0
                continue
            time_passed = BUFFER_LENGTH*counters[i]
            #phase = f*time_passed%(2*np.pi)
            rel_intensity = np.sqrt(f/base_freq)  # In order for all notes to play at same decibel. (uncertain about sqrt)
            if just_pressed[i]:
                temp_data += wave_cb(f, t+time_passed)*ramp_up/rel_intensity  # time_passed not necessary?
                just_pressed[i] = 0
            elif just_released[i]:
                temp_data += wave_cb(f, t+time_passed)*ramp_down/rel_intensity
                just_released[i] = 0
                active_freqs[i] = 0
            else:
                temp_data += wave_cb(f, t+time_passed)/rel_intensity

        just_released = np.zeros(16)
        old_scaling_factor = scaling_factor
        scaling_factor =  1/max(1, np.sum(active_freqs > 10))  # Number of "oscillators", min 1
        #scaling_factor = 1/(1+np.sqrt(np.sum(active_freqs > 10)))
        if old_scaling_factor == scaling_factor:
            temp_data = temp_data*scaling_factor
        else:
            scaling_ramp = np.linspace(old_scaling_factor, scaling_factor, BUFFER_FRAMES_NR)
            temp_data = temp_data*scaling_ramp
        """
        if np.amax(temp_data) > 1:
            print("Problem")
            save_data_0 = np.copy(np.frombuffer(data,dtype=np.float32))
            save_data_1 = np.copy(temp_data)
        """
        data = temp_data.astype(np.float32).tobytes()


def callback(in_data, frame_count, time_info, status):
    global data
    global mixed_flag
    global counters
    global just_released

    return_data = np.copy(data)
    mixed_flag = False
    counters += 1
    return (return_data, pyaudio.paContinue)

def set_chord_freqs(degree):
    global scale
    freqs = scale[degree : degree+16]
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
    global counters
    global transition_flag
    global residual_freqs
    global buttons
    # TODO: Add button for sharp and flat notes. Half done. not quite working smoothly
    # TODO: Change to switch-case?
    # Script does not enter this function when pressing 4 or 8 with 3+ chord tones playing

    key = event.keycode
    if key in key_dict_chord:
        index = key_dict_chord[key]
        active_freqs[index] = chord_freqs[index]
        just_pressed[index] = 1
        counters[index] = 0
    elif key in key_dict_scale:
        buttons[scale_degree].configure(bg="blue",fg="white")  # For GUI
        transition_flag = True
        scale_degree = key_dict_scale[key]
        buttons[scale_degree].configure(bg="yellow", fg="black")  # For GUI
        residual_freqs = np.copy(active_freqs)
        chord_freqs = set_chord_freqs(scale_degree)
        active_freqs = chord_freqs*(active_freqs > 10)
        just_pressed = np.ones(16)
    elif key in key_dict_misc:
        transition_flag = True
        action = key_dict_misc[key]
        if action == 0:
            scale = scale/ET_RATIO
            alt_scale = alt_scale/ET_RATIO
        elif action == 1:
            scale = scale*ET_RATIO
            alt_scale = alt_scale*ET_RATIO
        elif action == 2 or action == 3:
            scale, alt_scale = alt_scale, scale
        residual_freqs = np.copy(active_freqs)
        chord_freqs = set_chord_freqs(scale_degree)
        active_freqs = chord_freqs*(active_freqs > 10)
        just_pressed = np.ones(16)


def key_up(event):
    global active_freqs
    global just_released
    global just_pressed
    global scale
    global alt_scale
    global major_scale
    global scale_degree
    global active_freqs
    global chord_freqs
    global counters
    global transition_flag
    global residual_freqs

    key = event.keycode
    if key in key_dict_chord:
        index = key_dict_chord[key]
        just_released[index] = 1
    elif key in key_dict_misc:
        transition_flag = True
        action = key_dict_misc[key]
        if action == 0:
            scale = scale*ET_RATIO
            alt_scale = alt_scale*ET_RATIO
        elif action == 1:
            scale = scale/ET_RATIO
            alt_scale = alt_scale/ET_RATIO
        elif action == 2:
            scale, alt_scale = alt_scale, scale
        residual_freqs = np.copy(active_freqs)
        chord_freqs = set_chord_freqs(scale_degree)
        active_freqs = chord_freqs*(active_freqs > 10)
        just_pressed = np.ones(16)

chord_freqs = set_chord_freqs(0)

# Setting up tkinter
root = tk.Tk()
root.title("Kinda Synth")
root.configure(bg="black")

frame_1 = tk.Frame(root, height=200, width=1600, bg="black")
frame_1.pack()
frame_2 = tk.Frame(root, height=200, width=200, bg="blue")
frame_2.pack()

buttons = []
button_font = font.Font(family="Times", size=18, weight="bold")
for i in range(8):
    buttons.append(tk.Button(frame_1, text=chord_symb_dict_maj[i], bg="blue", fg="white", width=8, height=4, font=button_font))
    buttons[i].pack(padx=10, side=tk.LEFT)

buttons[0].configure(bg="yellow", fg="black")

root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)

p = PyAudio()
stream = p.open(format=pyaudio.paFloat32, 
                channels=1, 
                rate=BITRATE, 
                output=True,
                stream_callback=callback,
                frames_per_buffer=BUFFER_FRAMES_NR)
mixing(sine_fade)
root.mainloop()
stream.stop_stream()
stream.close()
p.terminate()
#plt.plot(t,save_data_0,'r',t,save_data_1,'b')
#plt.show()
os.system('xset r on')
"""
except:
    print("something went wrong")
    os.system('xset r on')
"""
