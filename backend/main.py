import cv2
import base64
import json
import asyncio
import torch
import time
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware # CORRECTED: Lowercase 'w'
from ultralytics import YOLO

# --- 0. CONFIGURATION AND INITIALIZATION ---
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🚀 RUNNING ON: {DEVICE}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware, # CORRECTED NAME
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⏳ LOADING STABILIZED AI MODEL...")
# Using the Medium model as requested
model = YOLO('yolov8m.pt') 
print("✅ SYSTEM READY.")

# Expanded Knowledge Base (with Detailed Instructions)
KNOWLEDGE_BASE = {
    # WASTE ITEMS (PLASTIC/METAL/ORGANIC)
    'bottle': {'category': 'PLASTIC', 'action': 'Recycle Bin (Blue)', 'color': '#3b82f6', 
               'steps': ["1. Empty completely.", "2. Rinse thoroughly with water.", "3. Remove the cap (recycle separately if plastic).", "4. Flatten the bottle to save space."], 
               'precautions': ["Ensure no liquid is left to prevent contamination.", "Check if the plastic type (PET, HDPE) is accepted locally."]},
    
    'cup': {'category': 'MIXED WASTE', 'action': 'General Waste (Black)', 'color': '#ef4444', 
            'steps': ["1. Remove any lids/straws.", "2. If heavily soiled with food/drink, place in general waste.", "3. If clean paper, compost or check local paper recycling."], 
            'precautions': ["Coffee cups (paper/wax lined) are often non-recyclable.", "Always separate plastic components from paper."]},
    
    'can': {'category': 'METAL', 'action': 'Recycle Bin (Blue)', 'color': '#fbbf24', 
            'steps': ["1. Ensure entirely empty.", "2. Rinse lightly to remove residue.", "3. Crush the can to save volume (optional)."], 
            'precautions': ["Do not recycle cans containing hazardous chemicals (paint, pesticides).", "Lids can be included if sharp edges are covered."]},
    
    'banana': {'category': 'ORGANIC', 'action': 'Compost Bin', 'color': '#22c55e', 
               'steps': ["1. Place peel directly into composting unit or designated organic bin.", "2. Do not use plastic bags."], 
               'precautions': ["Check local rules; some municipal composters do not accept fruit scraps.", "Avoid mixing with general waste."]},
    
    'book': {'category': 'PAPER', 'action': 'Recycle Bin (Blue)', 'color': '#34d399', 
             'steps': ["1. Remove hardcovers and any spiral metal bindings.", "2. Place softcover paper in the paper recycling bin."], 
             'precautions': ["Books heavily stained with liquid or oil should go in general waste.", "Do not bundle with strings."]},

    # HAZARDOUS/E-WASTE 
    'cell phone': {'category': 'E-WASTE', 'action': 'Special E-Waste Collection', 'color': '#f97316', 
                   'steps': ["1. DO NOT place in general or recycling bins.", "2. Back up and wipe all personal data.", "3. Remove the battery if possible.", "4. Drop off at a certified e-waste facility or retail take-back program."], 
                   'precautions': ["**HAZARD:** Batteries are highly reactive and pose a fire risk if crushed.", "Check for local hazardous waste collection days."]},
    
    'laptop': {'category': 'E-WASTE', 'action': 'Special E-Waste Collection', 'color': '#f97316', 
               'steps': ["1. DO NOT place in general or recycling bins.", "2. Wipe the hard drive/SSD completely.", "3. Take to a designated e-waste drop-off site.", "4. Utilize manufacturer take-back schemes."], 
               'precautions': ["**HAZARD:** Lithium batteries pose a fire risk if damaged.", "Personal data must be wiped completely before disposal."]},

    'scissors': {'category': 'HAZARDOUS', 'action': 'General Waste', 'color': '#dc2626', 
                 'steps': ["1. NEITHER compost nor recycle.", "2. Securely wrap the sharp points/edges with duct tape, cardboard, or bubble wrap.", "3. Place in the general waste bin."], 
                 'precautions': ["**SAFETY:** Wrapping is mandatory to protect sanitation workers from cuts."]},
    
    # NON-WASTE/IGNORED 
    'person': {'category': 'NON-WASTE', 'action': 'A Human Being', 'color': '#60a5fa', 'steps': ["Not a waste item."], 'precautions': ["Please place a recyclable object in the frame."]},

    # DEFAULT/UNKNOWN
    'default': {'category': 'SCANNING...', 'action': 'Awaiting object detection.', 'color': '#94a3b8', 'steps': ["No object detected in frame."], 'precautions': ["If the item is not detected, consult your local municipality's waste guide."]}
}

# --- 2. CAMERA UTILITY ---

def get_working_camera():
    """Tries common camera indices (0, 1, 2, 3) to find a working camera."""
    for index in range(4):
        # Explicitly use DirectShow backend for Windows stability
        camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if camera.isOpened():
            print(f"SUCCESS: Opened camera at index {index} using DSHOW.")
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return camera
        camera.release()
    print("ERROR: Could not find any working camera device (Indices 0-3 failed).")
    return None

# --- 3. VIDEO STREAM ENDPOINT ---

@app.websocket("/ws/video")
async def video_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    camera = get_working_camera()

    if camera is None:
        await websocket.send_text(json.dumps({"error": "Camera not found/available."}))
        return
    
    time.sleep(0.5) # Allow camera to stabilize

    SKIP_RATIO = 2
    frame_count = 0
    
    try:
        while True:
            success, frame = camera.read()
            if not success or frame is None: 
                await asyncio.sleep(0.01)
                continue
            
            frame_count += 1
            
            # --- DETECTION LOGIC ---
            if frame_count % SKIP_RATIO == 0:
                
                # Perform detection 
                results = model(frame, conf=0.15, device='cpu', verbose=False) # Use low conf for easy testing
                
                best_detection = None
                
                # Find the highest confidence detection
                for r in results:
                    for box in r.boxes:
                        label = model.names[int(box.cls[0])]
                        conf = float(box.conf[0])
                        
                        detection_data = KNOWLEDGE_BASE.get(label, KNOWLEDGE_BASE['default'])
                        
                        # Only track it if it's a known waste/e-waste item
                        if label in KNOWLEDGE_BASE and label != 'person':
                            if best_detection is None or conf > best_detection['conf']:
                                best_detection = {'label': label, 'conf': conf, 'data': detection_data}
                        
                # --- ANNOTATION AND REPORTING ---
                if best_detection and best_detection['conf'] > 0.15:
                    
                    # Draw bounding box on the frame
                    frame = results[0].plot(line_width=3)
                    
                    # Prepare data to send
                    final_report = best_detection['data'].copy() # Use .copy() to prevent modifying the KB directly
                    final_report['label'] = best_detection['label'].upper()
                    final_report['conf'] = best_detection['conf']
                    
                else:
                    # Default scanning state
                    final_report = KNOWLEDGE_BASE['default'].copy()
                    final_report['label'] = 'SCANNING...'
                    final_report['conf'] = 0.0

                # --- ENCODING AND SENDING ---
                _, buffer = cv2.imencode('.jpg', frame)
                img_b64 = base64.b64encode(buffer).decode('utf-8')
                
                await websocket.send_text(json.dumps({
                    "image": f"data:image/jpeg;base64,{img_b64}",
                    "data": final_report
                }))
                        
            await asyncio.sleep(0.001)

    except Exception as e:
        print(f"CRITICAL EXCEPTION IN VIDEO LOOP: {e}") 
    finally:
        if 'camera' in locals() and camera is not None:
             camera.release()