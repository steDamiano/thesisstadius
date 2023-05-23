from flask import Flask, render_template, Response, request, redirect, url_for

#from __future__ import print_function
import odrive
from odrive.enums import *
import time
import math

app = Flask(__name__)
speed = 0
forward_message = ""
rpm = 0
radius = 0.038

@app.route('/')
def index():
	return render_template('index.html')

@app.route("/calibrate/", methods=['POST'])
def calibrate_motor():
	print("Calibrating motor")
	forward_message = "Motor is calibrated"
	# Find a connected ODrive (this will block until you connect one)
	print("finding an odrive...")
	global odrv
	odrv = odrive.find_any()
	
	# 2)Apply new config
	print("applying config...")
	odrv.config.dc_bus_overvoltage_trip_level = 30
	odrv.config.dc_max_positive_current = 3
	odrv.config.dc_max_negative_current = -3
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
	odrv.axis0.controller.config.input_mode = InputMode.PASSTHROUGH
	odrv.axis0.controller.config.control_mode = ControlMode.VELOCITY_CONTROL
	odrv.axis0.controller.config.vel_limit = 10
	odrv.axis0.controller.config.vel_limit_tolerance = 15
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
	odrv.axis0.controller.config.vel_gain = 0.5
	
	# Calibrate motor and wait for it to finish
	print("starting calibration...")
	odrv.axis0.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
	while odrv.axis0.current_state != AxisState.IDLE:
	    time.sleep(0.1)
	return render_template('index.html', speed=speed, forward_message=forward_message)
	
@app.route("/start/", methods=['POST'])
def start_motor():
	#insert motor code
	print("Start pressed")
	rpm = (speed/(2*math.pi*radius))*(40/13)
	forward_message = "Motor is running at a speed of %s m/s" % (speed)
	odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
	odrv.axis0.controller.input_vel = rpm
	return render_template('index.html', speed=speed, forward_message=forward_message)

@app.route("/stop/", methods=['POST'])
def stop_motor():
	#insert motor code
	print("Stop pressed")
	forward_message = "Motor is stopped"
	odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
	odrv.axis0.controller.input_vel = 0
	return render_template('index.html', speed=speed, forward_message=forward_message)

@app.route("/speed/", methods=['GET', 'POST'])
def speed_motor():
	if request.method == 'POST':
		global speed
		speed = request.form['speed']
		speed = float(speed)
		print("The speed is %s" % (speed))
		forward_message = "Motor speed set to %s m/s" % (speed)
		#return '%s' % (speed)
		return render_template('index.html', speed=speed, forward_message=forward_message)
	else:
		return render_template('index.html', speed=speed, forward_message=forward_message)

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
