import sys
import time
import logging
import time
import math
import json

import odrive
from odrive.enums import *
# from ruckig import InputParameter, OutputParameter, Result, Ruckig
import matplotlib.pyplot as plt 
from copy import copy

try:
    from synchronization import ptp_master
except:
    from scripts.synchronization import ptp_master


class ODriveFailure(Exception):
    pass

class ODriveInterfaceAPI(object):
    driver = None
    encoder_cpr = 20480
    transmission_ratio = 14/32
    axis = None
    connected = False
    calibrated = False
    diameter_wheels = 0.076
    
    traj_start = None
    traj_end = None
    traj_waipoints = []
    times = []
    positions = []
    speeds = []
    
    #default speed & accel
    speed = 3
    accel = 3
    
    speed_limit = 20
    accel_limit = 10
    
    ptp_master = None
    
    def __init__(self, active_odrive = None):
        if active_odrive:
            self.driver = active_odrive
            self.axis = self.driver.axis
            self.encoder_cpr = self.driver.axis.encoder.config.cpr
            self.connected = True
            #self.calibrated = ...
        self.ptp_master = ptp_master.PTP_Master()
            
            
    def __del__(self):
        self.disconnect_odrive()
        
        
    def connect_odrive(self, port = None, timeout = 5):
        if self.driver:
            msg = ("already connected")
            print(msg, file=sys.stderr)
            return msg
        try: 
            self.driver = odrive.find_any(timeout = timeout)
        except:
            msg = ("no odrive found")
            print(msg, file=sys.stderr)
            return msg
        
        self.axis = self.driver.axis0
        
        #check for errors!
        
        self.encoder_cpr = self.driver.inc_encoder0.config.cpr
        self.connected = True
        self.calibrated = False
        
        return True
    
    
    def disconnect_odrive(self):
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
            msg = ("not connected")
            return msg
        
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
            msg = ("Error handling") + " \\ "
            msg += "Active errors: "+ str(self.axis.active_errors-1) + str(ODriveError(self.axis.active_errors-1)) + " \\ "
            msg += "Disarm reason: "+ str(self.axis.disarm_reason)+ str(ODriveError(self.axis.disarm_reason))
            return msg
        
        if self.axis.procedure_result != PROCEDURE_RESULT_SUCCESS:
            msg = ("Unsuccesful procedure: " + str(ProcedureResult(self.axis.procedure_result)))
            return msg
        
        self.calibrated = True
        return True
    
    
    def engaged(self):
        if self.driver and hasattr(self, 'axis'):
            return self.axis.current_state == AXIS_STATE_CLOSED_LOOP_CONTROL
        else:
            print("Odrive not connected")
            return False
    
    
    def idle(self):
        if not self.driver:
            return ("Odrive not connected")
    
        #self.logger.debug("Setting drive mode.")
        self.axis.requested_state = AXIS_STATE_IDLE
        
        if self.axis.active_errors != 0:
            msg = ("Error handling") + " \\ "
            msg += "Active errors: "+ str(self.axis.active_errors-1) + str(ODriveError(self.axis.active_errors-1)) + " \\ "
            msg += "Disarm reason: "+ str(self.axis.disarm_reason)+ str(ODriveError(self.axis.disarm_reason))
            return msg
        
        """
        if self.axis.procedure_result != PROCEDURE_RESULT_SUCCESS:
            msg = ("Unsuccesful procedure: " + str(ProcedureResult(self.axis.procedure_result)))
            return msg
        """
        
        #self.engaged = True
        return True
        
        
    def engage(self):
        if not self.driver:
            return ("Odrive not connected")
    
        #self.logger.debug("Setting drive mode.")
        self.axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        
        if self.axis.active_errors != 0:
            msg = ("Error handling") + " \\ "
            msg += "Active errors: "+ str(self.axis.active_errors-1) + str(ODriveError(self.axis.active_errors-1)) + " \\ "
            msg += "Disarm reason: "+ str(self.axis.disarm_reason)+ str(ODriveError(self.axis.disarm_reason))
            return msg
        
        """
        if self.axis.procedure_result != PROCEDURE_RESULT_SUCCESS:
            msg = ("Unsuccesful procedure: " + str(ProcedureResult(self.axis.procedure_result)))
            return msg
        """
        
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
            return "Odrive not connected"
        
        self.traj_start = self.axis.pos_vel_mapper.pos_rel
        return True;
    
    
    def set_traj_end(self):
        if not self.driver:
            return ("Odrive not connected")
        
        self.traj_end = self.axis.pos_vel_mapper.pos_rel
        return True;
    
    
    def go_to_start(self):
        return self.go_to(target_pos = self.traj_start)

         
    def go_to_end(self):
        return self.go_to(target_pos = self.traj_end)
       
    
    def go_to(self, target_pos, speed = None, accel = None):
        if not self.driver:
            return ("Odrive not connected")
         
        if not self.engaged():
            return ("Odrive not engaged")
         
        if not (self.traj_end):
            return("End of trajectory not yet set")
        
        if not (self.traj_start):
            return("Start of trajectory not yet set")
        
        if not ( ((self.traj_start <= target_pos) & (target_pos <= self.traj_end)) | ((self.traj_start >= target_pos) & (target_pos >= self.traj_end)) ):  
            return("Entered target position is outside of trajectory")
        
        if not speed:
            speed = self.speed
            
        if not accel:
            accel = self.accel
        
        if speed < self.speed_limit:
            self.axis.trap_traj.config.vel_limit = speed
        else:
            return ("Entered speed higher than speed limit of ", self.speed_limit, " rotations/s")

         
        if accel < self.accel_limit:
            self.axis.trap_traj.config.accel_limit = accel
            self.axis.trap_traj.config.decel_limit = accel
        else:
            print("Entered acceleration higher than speed limit of ", self.speed_limit, " rotations/s^2")

            
        self.axis.controller.input_pos = target_pos
        
        self.times = []
        self.positions = []
        self.speeds = []
        
        start_pos = self.axis.pos_vel_mapper.pos_rel
        start_time = time.time()
        while(abs(self.axis.pos_vel_mapper.pos_rel-target_pos) > 0.1):
            current_time = time.time()
            current_position = (self.axis.pos_vel_mapper.pos_rel - start_pos) * math.pi * self.diameter_wheels * self.transmission_ratio
            current_speed = self.axis.pos_vel_mapper.vel * math.pi * self.diameter_wheels * self.transmission_ratio
            
            self.times.append(current_time + self.ptp_master.offset_final)
            self.positions.append(current_position)
            self.speeds.append(current_speed)
            self.accurate_delay(0.0333333)            
        
        return True      

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
            return ("Odrive not connected")
        
        if self.speed_limit < speed:
            return "Speed higher than speed limit"
        
        self.speed = speed
        self.axis.trap_traj.config.vel_limit = self.speed
        return True
        
        
    def set_accel(self, accel):
        if not self.driver:
            return ("Odrive not connected")
        
        if self.accel_limit < accel:
            return "Acceleration higher than acceleration limit"
        
        self.accel = accel
        self.axis.trap_traj.config.accel_limit = self.accel
        self.axis.trap_traj.config.decel_limit = self.accel
        return True
        
    def synchronous_start(self):
        if not (self.ptp_master.check_connection()):
            return "Recording script at iMac not ready"
        
        if not self.engaged():
            return "Not engaged"
        
        if (self.ptp_master.sync_clock()):
            self.accurate_delay(3)
            if (self.go_to_end()):
                data = json.dumps({"times": self.times, "positions": self.positions, "speeds": self.speeds})
                self.ptp_master.send(data)
        
        return True
            
    def accurate_delay(self, delay):
        ''' Function to provide accurate time delay in seconds
        '''
        _ = (time.perf_counter() + delay)
        while time.perf_counter() < _:
            pass
            