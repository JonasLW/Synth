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
# TODO: Add custom keys functionality
# TODO: Make u key function as a duplicate of j
# TODO: Add button for dominant chords

os.system('xset r off')  # Turning off key-repeat

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
key_dict_misc = {"a":0,"s":1,"Shift_L":2,"Caps_Lock":3, "q":4}
chord_symb_dict_maj = {0:"Imaj7",1:"IIm7",2:"IIIm7",3:"IVmaj7",4:"V7",5:"VIm7",6:"VIIm7b5",7:"Imaj7"}
chord_symb_dict_min = {0:"Im7",1:"IIm7b5",2:"IIImaj7",3:"IVm7",4:"Vm7",5:"VImaj7",6:"VII7",7:"Im7"}
chord_symb_dict = chord_symb_dict_maj
alt_chord_symb_dict = chord_symb_dict_min


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

def custom_settings():
    global keycodes
    global values

    label = tk.Label(temp, text="")

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


base_freq = 2*np.pi*261.63  # Angular frequencies for performance, this this by option
semitones = np.empty(12)
for i in range(12):
    semitones[i] = base_freq*ET_RATIO**i

major_scale = np.copy(semitones[np.array([0,2,4,5,7,9,11])])
major_scale = np.concatenate((major_scale, 2*major_scale, 4*major_scale, 8*major_scale, 16*major_scale))
minor_scale = np.copy(semitones[np.array([0,2,3,5,7,8,10])])
minor_scale = np.concatenate((minor_scale, 2*minor_scale, 4*minor_scale, 8*minor_scale, 16*minor_scale))
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
dominant_flag = False
scaling_factor = 1

def sinewave(f, t):
    fade_in = 1 - 1/(2*t/BUFFER_LENGTH + 1)
    return np.sin(f*t)

def sine_fade(f, t):
    fade_in = 1 - 1/(2*t/BUFFER_LENGTH + 1)  # Does not work as intended
    return np.sin(f*t)*0.5**(t/0.5)

def sine_ramp_up(f, t):
    t_rel = t/BUFFER_LENGTH
    envelope = 4*t_rel/(t_rel+1)**2
    return np.sin(f*t)*envelope

def square(f, t):
    return signal.square(f*t)

def square_fade(f, t):
    return signal.square(f*t)*0.5**(t/0.5)

def saw(f, t):
    return signal.sawtooth(f*t)

def saw_fade(f, t):
    return signal.sawtooth(f*t)*0.5**(t/0.5)

def organ(f, t):
    return (0.1*np.sin(0.5*f*t)
            + np.sin(f*t)
            + 0.1*np.sin(3/2*f*t)
            + 0.05*np.sin(2*f*t)
            + 0.02*np.sin(8/3*f*t))/(0.1+1+0.1+0.05+0.02)

def organ_fade(f, t):
    return organ(f,t)*0.5**(t/0.5)

def square_sine(f, t):
    return (signal.square(f*t) + 0.3*np.sin(f*t))/1.3

def saw_sine(f, t):
    return signal.sawtooth(f*t)*np.sin(f*t)

def marimbish(f, t):
    # Weird sound found when trying to make a transient
    f_1 = np.sin(0.1*f*t)*0.5**(10*t)
    f_2 = np.sin(0.5*f*t)*0.5**(12*t)
    f_3 = np.sin(1.2*f*t)*0.5**(20*t)
    f_4 = np.sin(1.5*f*t)*0.5**(20*t)
    return (f_1 + f_2 + f_3 + f_4)/4

def transient(f, t):
    f_0 = np.sin(2*np.pi*130*t)*0.5**(20*t)
    f_1 = np.sin(2*8*np.sqrt(f*t))*0.5**(20*t)
    f_2 = np.sin(2*11*np.sqrt(f*t))*0.5**(22*t)
    f_3 = 0.5*np.sin(2*19*np.sqrt(f*t))*0.5**(40*t)
    f_4 = 0.2*np.sin(2*23*np.sqrt(f*t))*0.5**(40*t)
    return (f_1 + f_2 + f_3 + f_4)

def weird_sine(f, t):
    mod = 1 + np.sin(f/100*t)
    return np.sin(mod*f*t)*0.5**(t/0.5)

def sine_w_strike(f, t):
    return sine_fade(f, t) + transient(f, t)/4

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
    global dominant_flag
    freqs = np.copy(scale[degree : degree+16])
    if dominant_flag:
        base = scale[degree]
        third = base*ET_RATIO**4
        fifth = base*ET_RATIO**7
        seventh = base*ET_RATIO**10
        freqs[2] = third
        freqs[4] = fifth
        freqs[6] = seventh
        freqs[9] = 2*third
        freqs[11] = 2*fifth
        freqs[13] = 2*seventh
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
    global chord_buttons
    global tone_buttons
    global chord_symb_dict
    global alt_chord_symb_dict
    global dominant_flag
    # TODO: Change to switch-case?
    # Script does not enter this function when pressing 4 or 8 with 3+ chord tones playing

    key = event.keycode
    if key in key_dict_chord:
        index = key_dict_chord[key]
        active_freqs[index] = chord_freqs[index]
        just_pressed[index] = 1
        counters[index] = 0
        tone_buttons[scale_degree+index].configure(bg="yellow")
        if index%7 == 0:
            tone_buttons[scale_degree+index].configure(bg="white")
    elif key in key_dict_scale:
        transition_flag = True
        chord_buttons[scale_degree].configure(bg="blue",fg="white")  # For GUI
        [tone_buttons[i].configure(bg="black") for i in range(21)]
        scale_degree = key_dict_scale[key]
        chord_buttons[scale_degree].configure(bg="yellow", fg="black")  # For GUI
        residual_freqs = np.copy(active_freqs)
        chord_freqs = set_chord_freqs(scale_degree)
        active_freqs = chord_freqs*(active_freqs > 10)
        just_pressed = np.ones(16)
        for i in range(16):
            if active_freqs[i] > 10:
                tone_buttons[scale_degree+i].configure(bg="yellow")
                if i%7 == 0:
                    tone_buttons[scale_degree+i].configure(bg="white")
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
            chord_symb_dict, alt_chord_symb_dict = alt_chord_symb_dict, chord_symb_dict
            [chord_buttons[i].configure(text=chord_symb_dict[i]) for i in range(8)]
        elif action == 4:
            dominant_flag = True
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
    global tone_buttons
    global chord_symb_dict
    global alt_chord_symb_dict
    global dominant_flag

    key = event.keycode
    if key in key_dict_chord:
        index = key_dict_chord[key]
        just_released[index] = 1
        tone_buttons[scale_degree+index].configure(bg="black")
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
            chord_symb_dict, alt_chord_symb_dict = alt_chord_symb_dict, chord_symb_dict
            [chord_buttons[i].configure(text=chord_symb_dict[i]) for i in range(8)]
        elif action == 4:
            dominant_flag = False
        residual_freqs = np.copy(active_freqs)
        chord_freqs = set_chord_freqs(scale_degree)
        active_freqs = chord_freqs*(active_freqs > 10)
        just_pressed = np.ones(16)

def update_base_freq():
    global base_freq
    global scale
    global alt_scale
    global chord_freqs

    base_freq = 2*np.pi*float(v.get())
    semitones = np.empty(12)
    for i in range(12):
        semitones[i] = base_freq*ET_RATIO**i

    major_scale = np.copy(semitones[np.array([0,2,4,5,7,9,11])])
    major_scale = np.concatenate((major_scale, 2*major_scale, 4*major_scale, 8*major_scale, 16*major_scale))
    minor_scale = np.copy(semitones[np.array([0,2,3,5,7,8,10])])
    minor_scale = np.concatenate((minor_scale, 2*minor_scale, 4*minor_scale, 8*minor_scale, 16*minor_scale))
    scale = np.copy(major_scale)
    alt_scale = np.copy(minor_scale)
    chord_freqs = set_chord_freqs(scale_degree)
    frame_1.focus_set()




chord_freqs = set_chord_freqs(0)

# Setting up tkinter
root = tk.Tk()
root.title("Kinda Synth")
root.configure(bg="black")

frame_0 = tk.Frame(root, height=400, width = 200, bg="black")
frame_0.pack(side=tk.LEFT)
frame_1 = tk.Frame(root, height=200, width=1600, bg="black")
frame_1.pack()

v = tk.StringVar()
f_button = tk.Button(frame_0, text="Base frequency:", bg="blue", fg="white", command=update_base_freq)
f_button.pack(side=tk.LEFT, padx=10)
f_entry = tk.Entry(frame_0, width=8, textvariable=v)
f_entry.pack(side=tk.LEFT, padx=10)
v.set(str(base_freq/2/np.pi))

chord_buttons = []
button_font = font.Font(family="Times", size=18, weight="bold")
for i in range(8):
    chord_buttons.append(tk.Button(frame_1, text=chord_symb_dict_maj[i],
                             bg="blue", fg="white", width=8, height=4,
                             font=button_font))
    chord_buttons[i].grid(row=0, column=i, padx=10, pady=20)

chord_buttons[0].configure(bg="yellow", fg="black")

tone_buttons = []
button_font = font.Font(family="Times", size=18, weight="bold")
for i in range(21):
    tone_buttons.append(tk.Button(frame_1, bg="black", fg="white",
                                  width=1, height=1))
    tone_buttons[i].grid(row=3-i//7, column=i%7, pady=5)


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
