import cv2 
import numpy as np 
import os
import subprocess
import wave
from tqdm import tqdm

# ensure if 'out' and 'enc' directories exist
if not os.path.exists("out"): os.mkdr("out")
if not os.path.exists("enc"): os.mkdir("enc")

# path to encrypted file
enc_path = "out/covered.mkv"

# read the encrypted video file
enc = cv2.VideoCapture(enc_path)
enc_w = int(enc.get(3))
enc_h = int(enc.get(4))
enc_fps = enc.get(cv2.CAP_PROP_FPS)
enc_frame_cnt = enc.get(cv2.CAP_PROP_FRAME_COUNT)

# video writer for decoding secret video
out = cv2.VideoWriter('enc/decrypted_secret.avi', cv2.VideoWriter_fourcc(*"MJPG"), enc_fps/2, (enc_w, enc_h))

# working with audio
subprocess.call(f"ffmpeg -i {enc_path} enc/enc.wav", shell=True)

# decoding audio file
with wave.open("enc/dec.wav", 'wb') as d:
    e = wave.open("enc/enc.wav", 'rb')
    e_frames = np.array(list(e.readframes(e.getnframes())), dtype='uint8')

    # decryption of audio
    dec_frames = (e_frames&0b00001111)<<4

    d.setparams(e.getparams())
    d.writeframes(np.ndarray.tobytes(dec_frames))

    e.close()

# frame number 
fn = 0

# create a progress bar
pbar = tqdm(total=enc_frame_cnt, unit='frames')

while (1): 
    # let's take the decrypted image 
    ret, frame = enc.read() 
  
    if ret == False:
        break

    fn = fn + 1

    # for even frames, lower 2 bits are extracted
    # for odd frames, 3rd and 4th bits are extracted
    if (fn%2):
        decrypted_frame = (frame&0b00000011)<<4   
    else:
        decrypted_frame = decrypted_frame|(frame&0b00000011)<<6
        out.write(decrypted_frame)       
    
    pbar.update(1)

enc.release()
out.release()

# delete decrypted video if already exists
if os.path.exists("out/secret_revealed.mkv"): subprocess.call("rm -r out/secret_revealed.mkv", shell=True)

# save the secret video to a file
save_vid = "ffmpeg -i enc/decrypted_secret.avi -i enc/dec.wav -c:v copy out/secret_revealed.mkv"
subprocess.call(save_vid, shell=True)

# delete the temporary folder
subprocess.call("rm -r enc", shell=True)
