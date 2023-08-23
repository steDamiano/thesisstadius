import sys
import time
import logging

import odrive
from odrive.enums import *
from ruckig import InputParameter, OutputParameter, Result, Ruckig
import matplotlib.pyplot as plt 
from copy import copy


class ODriveFailure(Exception):
    pass

class ODriveInterfaceAPI(object):
    driver = None
    encoder_cpr = 20480
    transmission_ratio = 14/32
    axis = None
    connected = False
    calibrated = False
    
    traj_start = None
    traj_end = None
    traj_waipoints = []
    
    #default speed & accel
    speed = 3
    accel = 10
    
    speed_limit = 20
    accel_limit = 40
    
    def __init__(self, active_odrive = None):
        if active_odrive:
            self.driver = active_odrive
            self.axis = self.driver.axis
            self.encoder_cpr = self.driver.axis.encoder.config.cpr
            self.connected = True
            #self.calibrated = ...
            
            
    def __del__(self):
        self.disconnect()
        
        
    def connect(self, port = None, timeout = 5):
        if self.driver:
            print("already connected")
        try: 
            self.driver = odrive.find_any(timeout = timeout)
        except:
            print("no odrive found")
            return False
        
        self.axis = self.driver.axis0
        
        #check for errors!
        
        self.encoder_cpr = self.driver.inc_encoder0.config.cpr
        self.connected = True
        self.calibrated = False
        
        return True
    
    
    def disconnect(self):
        self.connected = False
        self.axis = None
        
        if not self.driver:
            print("not connected")
            return False
        
        try:
            self.release()
        except:
            return False
        finally:
            self.driver = None
        return True;
    
    
    def calibrate(self):
        if not self.driver:
            print("not connected")
            return False
        
        self.driver.config.dc_bus_overvoltage_trip_level = 33
        self.driver.config.dc_max_positive_current = 2
        self.driver.config.dc_max_negative_current = -2
        self.axis.config.motor.motor_type = MotorType.HIGH_CURRENT
        self.axis.config.motor.torque_constant = 0.05513333333333333
        self.axis.config.motor.pole_pairs = 7
        self.axis.config.motor.current_soft_max = 70
        self.axis.config.motor.current_hard_max = 90
        self.axis.config.motor.calibration_current = 10
        self.axis.config.motor.resistance_calib_max_voltage = 2
        self.axis.config.calibration_lockin.current = 10
        self.axis.controller.config.control_mode = ControlMode.POSITION_CONTROL
        self.axis.controller.config.input_mode = InputMode.TRAP_TRAJ
        self.axis.trap_traj.config.vel_limit = self.speed_limit
        self.axis.trap_traj.config.accel_limit = self.accel_limit
        self.axis.trap_traj.config.decel_limit = self.accel_limit
        self.axis.controller.config.vel_limit = self.speed_limit
        self.axis.controller.config.vel_limit_tolerance = 1
        self.axis.config.torque_soft_min = -0.7718666666666667
        self.axis.config.torque_soft_max = 0.7718666666666667
        self.driver.inc_encoder0.config.cpr = 20480
        self.driver.inc_encoder0.config.enabled = True
        self.driver.config.gpio7_mode = GpioMode.DIGITAL
        self.axis.commutation_mapper.config.use_index_gpio = True
        self.axis.commutation_mapper.config.index_gpio = 7
        self.axis.pos_vel_mapper.config.use_index_gpio = True
        self.axis.pos_vel_mapper.config.index_gpio = 7
        self.axis.pos_vel_mapper.config.index_offset = 0
        self.axis.pos_vel_mapper.config.index_offset_valid = True
        self.axis.config.load_encoder = EncoderId.INC_ENCODER0
        self.axis.config.commutation_encoder = EncoderId.INC_ENCODER0
        
        self.axis.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
        time.sleep(1)
        while self.axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            
        if self.axis.active_errors != 0:
            print("Error handling")
            print("Active errors: ", self.axis.active_errors-1, ODriveError(self.axis.active_errors-1))
            print("Disarm reason: ", self.axis.disarm_reason, ODriveError(self.axis.disarm_reason))
            return False
        
        if self.axis.procedure_result != PROCEDURE_RESULT_SUCCESS:
            print("Unsuccesful procedure: ", ProcedureResult(self.axis.procedure_result))
            return False
        
        self.calibrated = True
        return True
    
    
    def engaged(self):
        if self.driver and hasattr(self, 'axis'):
            return self.axis.current_state == AXIS_STATE_CLOSED_LOOP_CONTROL
        else:
            print("Odrive not connected")
            return False
    
    
    def idle(self):
        if self.driver and hasattr(self, 'axis'):
            return self.axis.current_state == AXIS_STATE_IDLE
        else:
            print("Odrive not connected")
            return False
        
        
    def engage(self):
        if not self.driver:
            print("Odrive not connected")
            return False
    
        #self.logger.debug("Setting drive mode.")
        self.axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        
        if self.axis.active_errors != 0:
            print("Error handling")
            print("Active errors: ", self.axis.active_errors-1, ODriveError(self.axis.active_errors-1))
            print("Disarm reason: ", self.axis.disarm_reason, ODriveError(self.axis.disarm_reason))
            return False
        
        if self.axis.procedure_result != PROCEDURE_RESULT_SUCCESS:
            print("Unsuccesful procedure: ", ProcedureResult(self.axis.procedure_result))
            return False
        
        
        #self.engaged = True
        return True
        
    
    def release(self):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        #self.logger.debug("Releasing.")
        self.axis.requested_state = AXIS_STATE_IDLE
    
        #self.engaged = False
        return True
        
    
    def set_traj_start(self):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        
        self.traj_start = self.axis.pos_vel_mapper.pos_rel
        return True;
    
    
    def set_traj_end(self):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        self.traj_end = self.axis.pos_vel_mapper.pos_rel
        return True;
    
    
    def go_to_start(self):
        return self.go_to(target_pos = self.traj_start)

         
    def go_to_end(self):
        return self.go_to(target_pos = self.traj_end)
       
    
    def go_to(self, target_pos, speed = None, accel = None):
        if not self.driver:
            print("Odrive not connected")
            return False
         
        if not self.engaged():
            print("Odrive not engaged")
            return False
         
        if not (self.traj_end):
            print("End of trajectory not yet set")
            return False
        
        if not (self.traj_start):
            print("Start of trajectory not yet set")
            return False
        
        if not ( ((self.traj_start <= target_pos) & (target_pos <= self.traj_end)) | ((self.traj_start >= target_pos) & (target_pos >= self.traj_end)) ):  
            print("Entered target position is outside of trajectory")
            return False
        
        if not speed:
            speed = self.speed
            
        if not accel:
            accel = self.accel
        
        if speed < self.speed_limit:
            print("Entered speed higher than speed limit of ", self.speed_limit, " rotations/s")
            self.axis.trap_traj.config.vel_limit = speed
         
        if accel < self.accel_limit:
            print("Entered acceleration higher than speed limit of ", self.speed_limit, " rotations/s^2")
            self.axis.trap_traj.config.accel_limit = accel
            self.axis.trap_traj.config.decel_limit = accel
            
        self.axis.controller.input_pos = target_pos
        
        times = []
        positions = []
        speeds = []
        
        start_pos = self.axis.pos_vel_mapper.pos_rel
        start_time = time.time()
        while(abs(self.axis.pos_vel_mapper.pos_rel-target_pos) > 0.1):
            current_time = time.time()
            current_position = self.axis.pos_vel_mapper.pos_rel
            current_speed = self.axis.pos_vel_mapper.vel
            
            times.append(current_time - start_time)
            positions.append(current_position - start_pos)
            speeds.append(current_speed)
            time.sleep(0.001)            
        
        # Calculate theoretical trajectory and plot it with measurements
        positions_th, speeds_th, accelerations_th, times_th = self.calculate_theoretical_traj(speed, accel, target_pos - start_pos)
        plt.plot(times, speeds, label = "Measurements")
        plt.plot(times_th, speeds_th, "--", label = "Theoretical")
        plt.title("Trajectory Position")
        plt.ylabel("Rotations/s")
        plt.xlabel("Time (s)")
        plt.legend(loc="upper left")
        plt.show()
        
        return True      
        
    def calculate_theoretical_traj(self, speed, accel, target_pos):
        otg = Ruckig(1, 0.01)  # DoFs, control cycle
        inp = InputParameter(1)
        out = OutputParameter(1)
     
        # Set input parameters
        inp.current_position = [0]
        inp.current_velocity = [0.0]
        inp.current_acceleration = [0.0]
     
        inp.target_position = [target_pos]
        inp.target_velocity = [0.0]
        inp.target_acceleration = [0.0]
     
        inp.max_velocity = [speed]
        inp.max_acceleration = [accel]
        inp.max_jerk = [100000]
      
        # Generate the trajectory within the control loop
        first_output, out_list = None, []
        positions, speeds, accelerations, times = [], [], [], []
        res = Result.Working
        while res == Result.Working:
            res = otg.update(inp, out)
     
            out_list.append(copy(out))
            times.append(out.time)
            positions.append(out.new_position)
            speeds.append(out.new_velocity)
            accelerations.append(out.new_acceleration)
            out.pass_to_input(inp)
     
            if not first_output:
                first_output = copy(out)
            
        return positions, speeds, accelerations, times
    
    def get_pos(self):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        return self.axis.pos_vel_mapper.pos_rel
    
    def get_speed(self):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        return self.axis.pos_vel_mapper.vel
    
    def set_speed(self, speed):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        if self.speed_limit < speed:
            return False
        
        self.speed = speed
        self.axis.trap_traj.config.vel_limit = self.speed
        return True
        
        
    def set_accel(self, accel):
        if not self.driver:
            print("Odrive not connected")
            return False
        
        if self.accel_limit < accel:
            return False
        
        self.accel = accel
        self.axis.trap_traj.config.accel_limit = self.accel
        self.axis.trap_traj.config.decel_limit = self.accel
        return True
    
    def get_traj_end(self):
        return self.traj_end
    
    def get_traj_start(self):
        return self.traj_start
        
        
        
           
           