import os
Audios_iMac_MAC = "a4:83:e7:e1:ed:07"
ethernetset = os.popen("arp -a").read().split('\n')
for response in ethernetset:
    if Audios_iMac_MAC in response:
        ADDRESS = response.split('(')[1].split(')')[0]