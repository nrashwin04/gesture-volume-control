import cv2
import mediapipe as mp
import numpy as np
import math
import platform
import subprocess

def main():
    sys_os = platform.system()
    volume = None
    min_vol, max_vol = 0, 100
    
    if sys_os == "Windows":
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        vol_range = volume.GetVolumeRange()
        min_vol = vol_range[0]
        max_vol = vol_range[1]

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

    cap = cv2.VideoCapture(0)
    
    smoothed_vol = 50.0
    alpha = 0.2
    
    while True:
        success, img = cap.read()
        if not success:
            break
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                h, w, c = img.shape
                
                x4, y4 = int(hand_landmarks.landmark[4].x * w), int(hand_landmarks.landmark[4].y * h)
                x8, y8 = int(hand_landmarks.landmark[8].x * w), int(hand_landmarks.landmark[8].y * h)
                x5, y5 = int(hand_landmarks.landmark[5].x * w), int(hand_landmarks.landmark[5].y * h)
                x17, y17 = int(hand_landmarks.landmark[17].x * w), int(hand_landmarks.landmark[17].y * h)
                
                cx, cy = (x4 + x8) // 2, (y4 + y8) // 2
                
                pinch_dist = math.hypot(x8 - x4, y8 - y4)
                hand_span = math.hypot(x17 - x5, y17 - y5)
                
                if hand_span > 0:
                    ratio = pinch_dist / hand_span
                else:
                    ratio = 0
                    
                raw_vol = np.interp(ratio, [0.15, 1.2], [0, 100])
                
                smoothed_vol = alpha * raw_vol + (1.0 - alpha) * smoothed_vol
                vol_percent = int(smoothed_vol)
                
                if sys_os == "Windows" and volume is not None:
                    target_vol = np.interp(vol_percent, [0, 100], [min_vol, max_vol])
                    volume.SetMasterVolumeLevel(target_vol, None)
                elif sys_os == "Darwin":
                    subprocess.run(["osascript", "-e", f"set volume output volume {vol_percent}"])
                elif sys_os == "Linux":
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{vol_percent}%"], stdout=subprocess.DEVNULL)
                
                print(f"Volume: {vol_percent}%")
                
                cv2.circle(img, (x4, y4), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x8, y8), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x4, y4), (x8, y8), (255, 0, 255), 3)
                
                if ratio < 0.25:
                    cv2.circle(img, (cx, cy), 10, (0, 255, 0), cv2.FILLED)
                else:
                    cv2.circle(img, (cx, cy), 10, (255, 255, 255), cv2.FILLED)
                    
                vol_bar = np.interp(vol_percent, [0, 100], [400, 150])
                
                cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)
                cv2.rectangle(img, (50, int(vol_bar)), (85, 400), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, f'{vol_percent} %', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 3)

        cv2.imshow("Hand-Gesture Volume Control", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
