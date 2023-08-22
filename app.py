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
    try:
        """
        global odrv
        odrv = odrive.find_any(timeout=5)
        print("Odrive found", file=sys.stderr)
        # forward_message = "ODrive found"
        """

        forward_message = "ODrive V3"  # TODO: Aanapssen naar naam van ODrive
        update_debug_window(forward_message)
        od.connect()
    except TimeoutError:
        print("No ODrives found.", file=sys.stderr)
        forward_message = "No ODrives found."
        update_debug_window(forward_message)
    except:
        print("Unknown error, check source.", file=sys.stderr)
        forward_message = "Unknown error, check source."
        update_debug_window(forward_message)
    return (forward_message)
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/calibrate/")
def calibrate_motor():
    try:
        od.calibrate()

        """
        print("Applying config...", file=sys.stderr)

        update_debug_window("Applying config...")
        odrv.config.dc_bus_overvoltage_trip_level = 30
        odrv.config.dc_max_positive_current = 2
        odrv.config.dc_max_negative_current = -2
        odrv.axis0.config.motor.motor_type = MotorType.HIGH_CURRENT
        odrv.axis0.config.motor.torque_constant = 0.05513333333333333
        odrv.axis0.config.motor.pole_pairs = 7
        odrv.axis0.config.motor.current_soft_max = 70
        odrv.axis0.config.motor.current_hard_max = 90
        odrv.axis0.config.motor.calibration_current = 10
        odrv.axis0.config.motor.resistance_calib_max_voltage = 2
        odrv.axis0.config.torque_soft_min = -0.7718666666666667
        odrv.axis0.config.torque_soft_max = 0.7718666666666667
        odrv.axis0.config.calibration_lockin.current = 10
        odrv.axis0.controller.config.control_mode = ControlMode.VELOCITY_CONTROL
        odrv.axis0.controller.config.input_mode = InputMode.VEL_RAMP
        odrv.axis0.controller.config.vel_ramp_rate = 1
        odrv.axis0.controller.config.vel_limit = 20
        odrv.axis0.controller.config.vel_limit_tolerance = 5
        odrv.inc_encoder0.config.cpr = 8192
        odrv.inc_encoder0.config.enabled = True
        odrv.config.gpio7_mode = GpioMode.DIGITAL
        odrv.axis0.commutation_mapper.config.use_index_gpio = True
        odrv.axis0.commutation_mapper.config.index_gpio = 7
        odrv.axis0.pos_vel_mapper.config.use_index_gpio = True
        odrv.axis0.pos_vel_mapper.config.index_gpio = 7
        odrv.axis0.pos_vel_mapper.config.index_offset = 0
        odrv.axis0.pos_vel_mapper.config.index_offset_valid = True
        odrv.axis0.config.load_encoder = EncoderId.INC_ENCODER0
        odrv.axis0.config.commutation_encoder = EncoderId.INC_ENCODER0

        # Calibrate motor and wait for it to finish
        print("Starting calibration...", file=sys.stderr)
        update_debug_window("Starting calibration...")
        odrv.axis0.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
        while odrv.axis0.current_state != AxisState.IDLE:
            time.sleep(0.1)
        if (odrv.axis0.active_errors != 0):
            #forward_message = "Calibration unsuccesful"
            print("Could not calibrate, Error: " + str(odrv.axis0.active_errors), file=sys.stderr)
            forward_message = "Could not calibrate" + str(odrv.axis0.active_errors)
            update_debug_window(forward_message)
        else:
            print("Calibration finished.", file=sys.stderr)
            forward_message = "Calibration finished"
            update_debug_window(forward_message)
        """
        forward_message = "Calibration finished"
        update_debug_window(forward_message)
    except:
        print("No ODrive connected.", file=sys.stderr)
        forward_message = "No ODrive connected."
        update_debug_window(forward_message)
    return forward_message
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/start/")
def start_motor():
    try:
        # insert motor code
        print("Start pressed", file=sys.stderr)
        odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        rps = (speed / (2 * math.pi * radius)) * (32 / 14)
        odrv.axis0.controller.input_vel = rps
        forward_message = "Motor is running at a speed of %s m/s" % (speed)
        update_debug_window(forward_message)
    except:
        print("No ODrive connected.", file=sys.stderr)
        forward_message = "No ODrive connected."
        update_debug_window(forward_message)
    return forward_message
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/stop/")
def stop_motor():
    try:
        # insert motor code
        print("Stop pressed")
        odrv.axis0.controller.input_vel = 0
        forward_message = "Motor is stopped"
        update_debug_window(forward_message)

        while odrv.axis0.pos_vel_mapper.vel > 0.5:
            time.sleep(0.1)

        odrv.axis0.requested_state = AXIS_STATE_IDLE
    except:
        print("No ODrive connected.", file=sys.stderr)
        forward_message = "No ODrive connected."
        update_debug_window(forward_message)
    return forward_message
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/speed/", methods=['POST'])
def speed_motor():
    # try:
    if request.method == 'POST':
        global speed
        speed = request.json['speedData']
        print(speed)
        speed = float(speed)
        rps = (speed / (2 * math.pi * radius)) * (32 / 14)
        od.set_speed(rps)
        print("The speed is %s" % (speed))
        forward_message = "Motor speed set to %s m/s" % (speed)
        update_debug_window(forward_message)
        return forward_message
        # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)
    else:
        return "TODO: Change dit"
        # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)
    # except:
    #     print("No ODrive connected.", file=sys.stderr)
    #     forward_message = "No ODrive connected."
    #     update_debug_window(forward_message)
    # return forward_message
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/recordTrack/")
def record_track():
    global track_distance
    try:
        # Insert encoder code
        start_pos = odrv.axis0.config.encoder.pos_estimate
        odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        odrv.axis0.controller.input_vel = 5

        odrv.axis0.controller.input_vel = 0
        track_distance = 10  # TODO: Aanpassen
        forward_message = "Track distance equals to %s m" % (track_distance)
        update_debug_window(forward_message)
    except:
        track_distance = 1  # TODO: Aanpassen
        print("No ODrive connected.", file=sys.stderr)
        forward_message = "No ODrive connected."
        update_debug_window(forward_message)
    return str(track_distance)
    # return render_template('index.html', speed=speed, forward_message=forward_message, track_distance=track_distance, current_speed=current_speed)


@app.route("/setStart/")
def set_start():
    od.set_traj_start()
    forward_message = "Track start is set"
    return forward_message


@app.route("/setEnd/")
def set_end():
    od.set_traj_end()
    # track_distance = 3
    track_distance = ((od.get_traj_end() - od.get_traj_start()) * (2 * math.pi * radius)) / (32 / 14)
    od.engage()

    return str(round(track_distance,2))


@app.route("/playTrack/")
def play_track():
    # Insert motor code
    od.go_to_end()
    forward_message = "Track play successful"
    return forward_message


@app.route("/resetPos/")
def reset_pos():
    # Insert motor code
    od.go_to_start()
    forward_message = "Position reset successful"
    return forward_message


@app.route("/setConditions/", methods=['POST'])
def set_conditions():
    global data
    data = request.json['conditionsData']
    speed = data.cond-speedDistance
    rps = (speed / (2 * math.pi * radius)) * (32 / 14)
    od.set_speed(rps)
    print(str(data))
    return jsonify({'data': data})


@app.route("/cartData")
def cart_data():
    try:
        current_vel = od.get_speed()
        current_speed = round(((current_vel) * (2 * math.pi * radius)) / (32 / 14),2)
        start_pos = round(od.get_traj_start(),2)
        end_pos = round(od.get_traj_end(),2)
        templateData = {'vel': current_speed, 'startPos': start_pos, 'endPos': end_pos}
        return jsonify(templateData), 200
    except:
        current_vel = 0
        templateData = {'vel': current_vel}
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
