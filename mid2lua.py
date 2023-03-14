import sys
import os
import mido
import pretty_midi
import math
import time

import warnings

warnings.filterwarnings("ignore")

midi_file_paths = []

if len(sys.argv) > 1:
	midi_file_paths = sys.argv[1:]
else:
	print('No files were found! Drag your .mid files into the "Midi2Module.exe" program.')
	print("")
	print("You can close this window.")
	time.sleep(5)

for midi_file_path in midi_file_paths:
	
	mido_data = mido.MidiFile(midi_file_path)
	pretty_data = pretty_midi.PrettyMIDI(midi_file_path)
	
	data = {}
	
	# Retrieving Time Signature
	numerator, denominator = pretty_data.time_signature_changes[0].numerator, pretty_data.time_signature_changes[
		0].denominator
	data['tempo'] = None
	data['signature'] = f'{numerator}/{denominator}'
	data['skips'] = []
	data['notes'] = []
	
	# Retrieving Notes, Tempo, and Skips
	ticks_per_beat = None
	microseconds_per_beat = None
	cumulative_ticks = 0
	for track in mido_data.tracks:
		# Keep track of notes that are currently on and their start times
		active_notes = {}
		for msg in track:
			if msg.type == 'set_tempo':
				# The tempo message stores BPM in microseconds per quarter note
				microseconds_per_beat = msg.tempo
				data['tempo'] = round(mido.tempo2bpm(msg.tempo))
			else:
				# Calculate the number of ticks per beat based on the MIDI file's timing resolution
				ticks_per_beat = mido_data.ticks_per_beat
				# Update the cumulative tick count for delta-time encoding
				cumulative_ticks += msg.time
				if msg.type == 'note_on':
					# Keep track of the start time of this note
					active_notes[msg.note] = mido.tick2second(cumulative_ticks, ticks_per_beat, microseconds_per_beat)
				elif msg.type == 'note_off':
					note_name = pretty_midi.note_number_to_name(msg.note)
					# Calculate the time in seconds when the note starts relative to the start of the song
					time_in_seconds = active_notes[msg.note]
					# Calculate the end time of the note by adding the note_duration of the note to the start time
					note_duration = mido.tick2second(cumulative_ticks, ticks_per_beat, microseconds_per_beat) - time_in_seconds
					if not (note_name == 'G9' or note_name == 'C-1'):
						data['notes'].append(
							[
								note_name, math.ceil(time_in_seconds * 60),
								math.ceil((time_in_seconds + note_duration) * 60)
							]
						)
					else:
						data['skips'].append(math.ceil(time_in_seconds * 60))
					# Remove the note from the active_notes dictionary
					del active_notes[msg.note]
	last_note_time = data['notes'][-1][-1]
	
	# Output
	output_file_path = os.path.splitext(midi_file_path)[0] + '.lua'
	with open(output_file_path, 'w') as f:
		f.write(f'-- Original file: "{os.path.splitext(midi_file_path)[0]}.mid"\n')
		f.write('return {\n')
		for name, value in data.items():
			if name == 'skips':
				# Write Skips
				if len(value) >= 2:
					f.write(f'	{name} = {{{value[0]},{value[1]}}},\n')
				else:
					f.write(f'	{name} = {{{0},{last_note_time}}},\n')
			elif name == 'notes':
				# Write Notes
				f.write(f'	{name} = {{\n')
				f.write("".join(f'		{{"{n[0]}",{n[1]}}},\n' for n in value))
				f.write('    }\n')
			else:
				f.write(f'	{name} = "{value}",\n')
		f.write('}\n')
		print(f"Successfully converted {midi_file_path} into a Lua file...")
