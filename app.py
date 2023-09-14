from flask import Flask, render_template, Response, request, redirect, url_for
from flask.json import jsonify
import time
import subprocess

import sys
import odrive
# from fibre.libfibre import ObjectLostError
from odrive.enums import *
import time
import math

from scripts import odrive_interface

app = Flask(__name__)
speed = 0
forward_message = ""
rpm = 0
radius = 0.038
track_distance = 0
data = ""
current_speed = 0
debug_messages = []

od = odrive_interface.ODriveInterfaceAPI()


# template = render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/findOdrive/")
def find_odrive():
    print("Finding an ODrive...", file=sys.stderr)
    forward_message = "Finding an ODrive..."
    update_debug_window(forward_message)
    
    result = od.connect_odrive()
    
    if (result == True):
        forward_message = "ODrive PRO" 
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)


@app.route("/calibrate/")
def calibrate_motor():
    update_debug_window("Starting Calibration...")
    
    result = od.calibrate()
    
    if (result == True):
        forward_message = "Calibration finished"
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)


@app.route("/speed/", methods=['POST'])
def speed_motor():
    # try:
    if request.method == 'POST':
        global speed
        speed = request.json['speedData']
        print(speed)
        speed = float(speed)
        rps = (speed / (math.pi * od.diameter_wheels)) / od.transmission_ratio
        
        result = od.set_speed(rps)
        
        if (result == True):
            forward_message = "Motor speed set to %s m/s" % (speed)
        else:
            update_debug_window(result)
            forward_message = result
            
        return (forward_message)
    else:
        return "TODO: Change dit"
    
@app.route("/accel/", methods=['POST'])
def accel_motor():
    # try:
    if request.method == 'POST':
        global accel
        accel = request.json['accelData']
        accel = float(accel)
        aps = (accel / (math.pi * od.diameter_wheels)) / od.transmission_ratio
        
        result = od.set_accel(aps)
        
        if (result == True):
            forward_message = "Motor acceleration set to %s m/s²" % (accel)
        else:
            update_debug_window(result)
            forward_message = result
            
        return (forward_message)
    else:
        return "TODO: Change dit"
    

@app.route("/goto/", methods=['POST'])
def go_to():
    # try:
    if request.method == 'POST':
        global goto
        goto = request.json['gotoData']
        result = float(goto)
        goto = (goto / (math.pi * od.diameter_wheels)) / od.transmission_ratio
        
        try:
            goto = goto + od.traj_start
        except:
            return "Trajectory not yet defined"
        
        result = od.go_to(goto)
        
        if (result == True):
            forward_message = "Moving to %s m" % (result)
        else:
            update_debug_window(result)
            forward_message = result
            
        return (forward_message)
    else:
        return "TODO: Change dit"



@app.route("/setStart/")
def set_start():
    result = od.set_traj_start()
    
    if (result == True):
        forward_message = "Start has been set" 
    else:
        update_debug_window(result)
        forward_message = result
        
    try:
        track_distance = ((od.traj_end - od.traj_start) * (math.pi * od.diameter_wheels)) * (od.transmission_ratio)
    except:
        track_distance = 0
    return str(round(track_distance,2))


@app.route("/setEnd/")
def set_end():
    result = od.set_traj_end()
    
    if (result == True):
        forward_message = "End has been set" 
    else:
        update_debug_window(result)
        forward_message = result
    try:
        track_distance = ((od.traj_end - od.traj_start) * (math.pi * od.diameter_wheels)) * (od.transmission_ratio)
    except:
        track_distance = 0
    return str(round(track_distance,2))


@app.route("/engage/")
def engage():
    result = od.engage()
    
    if (result == True):
        forward_message = "Motor state: engaged" 
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)

@app.route("/idle/")
def idle():
    result = od.idle()
    
    if (result == True):
        forward_message = "Motor state: idle" 
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)

@app.route("/playTrack/")
def play_track():
    result = od.go_to_end()
    
    if (result == True):
        forward_message = "Arrived at end" 
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)



@app.route("/resetPos/")
def reset_pos():
    result = od.go_to_start()
    
    if (result == True):
        forward_message = "Arrived at start" 
    else:
        update_debug_window(result)
        forward_message = result
        
    return (forward_message)


@app.route("/cartData")
def cart_data():
    try:
        current_vel = od.get_speed()
        current_speed = round(((current_vel) * (math.pi * od.diameter_wheels)) * od.transmission_ratio,2)
        templateData = {'vel': current_speed}
        return jsonify(templateData), 200
    except Exception as e:
        current_vel = 69
        templateData = {'vel': current_vel}
        print(e, file=sys.stderr)
        return jsonify(templateData), 200


@app.route('/debug_messages/')
def get_debug_messages():
    return jsonify(debug_messages)


def update_debug_window(message):
    debug_messages.append(message)


@app.context_processor
def inject_debug_messages():
    return {'debug_messages': debug_messages}


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
