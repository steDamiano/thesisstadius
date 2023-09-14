import socket
import sys
from datetime import datetime
import time
import numpy as np
import sounddevice as sd
import time
import soundfile as sf
import os

class PTP_Master(object):
    """ Connectio Info """
    server_socket = None
    connected = False
    PORT = 2468
    SLAVE_ADDRESS = "192.168.42.227"
    NUM_OF_TIMES = 20

    OFFSETS = []
    DELAYS = []
    
    synced_time = None
    
    """ Audio Info """
    device = None
    frequency = 5000
    amplitude = 0.5
    samplerate = sd.query_devices(device, 'output')['default_samplerate']
    sd.default.latency = 'high'
    sine_stream = None
    start_idx = 0
    play_sine = False
    
    def __init__(self, active_odrive = None):
        self.setup()
        
    def setup(self):
        self.sine_stream = sd.OutputStream(device=self.device, channels=1, callback=self.sine_callback,
                         samplerate=self.samplerate)
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.settimeout(5)
        except Exception as e:
            print("Error creating socket: " + str(e) + ". Exitting ...")
            self.server_socket.close()
    
        try:
            self.server_socket.connect((self.SLAVE_ADDRESS, self.PORT))
        except Exception as e:
            print("Error creating socket: " + str(e) + ". Exitting ...")
            self.server_socket.close()
        
    def sine_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        t = (self.start_idx + np.arange(frames)) / self.samplerate
        t = t.reshape(-1, 1)
        outdata[:] = self.amplitude * np.sin(2 * np.pi * self.frequency * t)
        self.start_idx += frames
    
    
    def sync_clock(self):
        self.OFFSETS = []
        self.DELAYS = []
        
        print("\nSyncing time with " + self.SLAVE_ADDRESS + ":" + str(self.PORT) + " ...")

        if not self.check_connection():
            print("Slave at: " + self.SLAVE_ADDRESS + " is not ready or does not exist.")
            """
            print("Pinging slave IP... ")
            response = os.system("ping -c 1 " + self.SLAVE_ADDRESS)
            print("Response: ", response)
            """
            return False
        
        try:
            self.send("sync")
            t, resp = self.recv()
            self.send(str(self.NUM_OF_TIMES))
        
            t, resp = self.recv()
        
            if(resp == "ready"):
                time.sleep(1)  # to allow for server to get ready
                for i in range(self.NUM_OF_TIMES):
                    ms_diff = self.sync_packet()
                    sm_diff = self.delay_packet()
        
                    offset = (ms_diff - sm_diff)/2
                    delay = (ms_diff + sm_diff)/2
        
                    self.OFFSETS.append(offset)
                    self.DELAYS.append(delay)
                    self.send("next")
                
                offset_final = sum(self.OFFSETS) / len(self.OFFSETS)
                delay_final = sum(self.DELAYS) / len(self.DELAYS)
                print('Final offset: ', offset_final)
                print('Final delay: ', delay_final)
                
                self.send("start_recording")
                self.accurate_delay(1)
                self.send('synced_execute')
    
                delay = 1 # both computers agree to start at time.time() + delay based on this computer's clock
                
                time_to_start = self.get_time() + delay
                self.send(str(time_to_start + offset_final))
                
                time_to_wait = time_to_start - self.get_time()
                self.accurate_delay(time_to_wait)
                self.synced_time = self.get_time() + offset_final
                
                print("Synced time: ", self.synced_time)
                print("Stream latency: ", self.sine_stream.latency)
                print("Succesfull packets: ", len(self.OFFSETS))
                #play sine wave that indicates synchronisation
                if not self.play_sine:
                    return True
                else:
                    with self.sine_stream:
                        self.accurate_delay(1)
                    return True
        
        except Exception as e:
            print("Error syncing times")
            print(e)
            return False
                
    def accurate_delay(self, delay):
        _ = time.perf_counter() + delay
        while time.perf_counter() < _:
            pass
    
    def sync_packet(self):
        t1 = self.send("sync_packet")
        t, t2 = self.recv()
        return float(t2) - float(t1)
    
    
    def delay_packet(self):
        self.send("delay_packet")
        t4, t3 = self.recv()
        return float(t4) - float(t3)
    
    
    def recv(self):
        try:
            msg = self.server_socket.recv(4096)
            t = self.get_time()
            return (t, msg.decode("utf8"))
        except Exception as e:
            print("Error while receiving request: " + str(e))
            self.server_socket.close()
    
    
    def send(self, data):
        try:
            self.server_socket.sendall(data.encode('utf8'))
            t = self.get_time()
            return t
            # print "Sent:" + str(data)
        except Exception as e:
            print("Error while sending request: " + str(e))
            print("Tried to send: " + data)

    
    def check_connection(self):
        self.setup()
        try:
            self.server_socket.sendall("check_connection".encode('utf8'))
            msg = self.server_socket.recv(4096).decode("utf8")
            if (msg == "ready"):
                return True
        except:
            return False
        
        
    def toggle_play_sine(self):
        self.play_sine = not self.play_sine
        return self.play_sine
    
    
    def get_time(self):
        return time.time()
    
    