import cv2
import numpy as np
import subprocess
import os
from tqdm import tqdm
import wave

# configure for encryption
if not os.path.exists("enc"): os.mkdir("enc") 
if not os.path.exists("out"): os.mkdir("out") 

# path of cover video and secret video
cover_path = "v1.mp4"
secret_path = "v2.mp4"

# counting the frame to tract the position
fn = 0

# -- resize keeping aspect ratio constant -- #
def resize(src, w=None, h=None, ar=None):
    """
    Resizes keeping aspect ratio
    src: Source File
    w: Width to be reached
    h: Height to be reached
    ar: aspect ratio for operation
    """

    if w is not None and h is not None:
        return cv2.resize(src, (w, h))
    assert(ar != None)
    if w is not None:
        return cv2.resize(src, (w, int(w/ar)))
    if h is not None:
        return cv2.resize(src, (int(h*ar), h))

# Video Objects for src and secret
src = cv2.VideoCapture(cover_path)
src_w = int(src.get(3))
src_h = int(src.get(4))
src_fps = src.get(cv2.CAP_PROP_FPS)
src_frame_cnt = src.get(cv2.CAP_PROP_FRAME_COUNT)

sec = cv2.VideoCapture(secret_path)
sec_w = int(sec.get(3))
sec_h = int(sec.get(4))
sec_fps = sec.get(cv2.CAP_PROP_FPS)
sec_frame_cnt = sec.get(cv2.CAP_PROP_FRAME_COUNT)

if src_frame_cnt < sec_frame_cnt:
    print("please choose the cover video with higher duration length than secret video")
    exit()

# working with audio 
sec_duration = sec_frame_cnt/sec_fps
subprocess.call(f"ffmpeg -ss 0 -t {sec_duration} -i {cover_path} enc/cvr.wav", shell=True)
subprocess.call(f"ffmpeg -ss 0 -t {sec_duration} -i {secret_path} enc/scr.wav", shell=True)

# encoding audio
# well this technique is very noisy for audio encryption
with wave.open("enc/enc.wav", 'wb') as e:
    s = wave.open("enc/scr.wav", 'rb')
    c = wave.open("enc/cvr.wav", 'rb')
    s_frames = np.array(list(s.readframes(s.getnframes())), dtype='uint8')
    c_frames = np.array(list(c.readframes(c.getnframes())), dtype='uint8')
	
	# make the shape of frames same
    if s_frames.shape[0]>c_frames.shape[0]:
      c_frames = np.concatenate((c_frames, np.zeros((s_frames.shape[0]-c_frames.shape[0],), dtype='uint8')), axis=0)
    elif s_frames.shape[0]<c_frames.shape[0]:
      s_frames = np.concatenate((s_frames, np.zeros((c_frames.shape[0]-s_frames.shape[0],), dtype='uint8')), axis=0)

    # encryption of audio
    enc_frames = (c_frames&0b11110000)|(s_frames&0b11110000)>>4

    e.setparams(s.getparams())
    e.writeframes(np.ndarray.tobytes(enc_frames))

    s.close()
    c.close()

# create a progress bar
pbar = tqdm(total=sec_frame_cnt*2, unit='frames')

while(1):
    _, src_frame = src.read()
    ret, sec_frame = sec.read()

    if ret == False:
	    break

    # get aspect ratio
    src_ar = src_w/src_h
    sec_ar = sec_w/sec_h

    # secret video may loose video quality if its resolution is higher then cover video 
    # -- fit the cover frame -- #
    if src_ar == sec_ar and src_frame.shape < sec_frame.shape:
        sec_frame = resize(sec_frame, src_w, src_h)
    elif src_ar != sec_ar and (src_w < sec_w or src_h < sec_h):
        if sec_w>sec_h:
            sec_frame = resize(sec_frame, w=src_w, ar=sec_ar)
            if sec_frame.shape[0]>src_h:
                sec_frame = resize(sec_frame, h=src_h, ar=sec_ar)
        else:
            sec_frame = resize(sec_frame, h=src_h, ar=sec_ar)
            if sec_frame.shape[1]>src_w:
                sec_frame = resize(sec_frame, w=src_w, ar=sec_ar)

    # -- fill the remaining pixel with black color -- #
    sec_frame = cv2.hconcat([sec_frame, np.zeros((sec_frame.shape[0], src_w-sec_frame.shape[1], 3), dtype='uint8')])
    sec_frame = cv2.vconcat([sec_frame, np.zeros((src_h-sec_frame.shape[0], sec_frame.shape[1], 3), dtype='uint8')])

    # -- encryption for LSB 2 bits -- #
    encrypted_img = (src_frame&0b11111100)|(sec_frame>>4&0b00000011)
    fn = fn + 1
    cv2.imwrite("enc/{}.png".format(fn), encrypted_img)

    # -- encryption for 3rd and 4th bits from LSB side-- #
    encrypted_img = (src_frame&0b11111100)|(sec_frame>>6)
    fn = fn + 1
    cv2.imwrite("enc/{}.png".format(fn), encrypted_img)

    pbar.update(2)

pbar.close()

src.release()
sec.release()

# delete encrypted video if already exists
if os.path.exists("out/covered.mkv"): subprocess.call("rm -r out/covered.mkv", shell=True)

# save the video using ffmpeg as a lossless video
# frame rate is doubled to preserve the speed of cover video
save_vid = "ffmpeg -framerate {} -i enc/%d.png -i enc/enc.wav -c:v copy -c:av copy out/covered.mkv".format(src_fps*2)
subprocess.call(save_vid, shell=True)

# delete the temporary image sequence folder
subprocess.call("rm -r enc", shell=True)
