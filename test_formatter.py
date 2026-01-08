from formatter import format_status

example_output = "{'name': 'Surau', 'type': 'AC2936', 'modelid': 'AC2936/33', 'MCUBoot': True, 'swversion': 'Ms2106', 'language': 'EN', 'country': 4, 'color': 0, 'DeviceVersion': '1.0.6', 'range': 'MarsLE', 'Runtime': 246330088, 'rssi': -43, 'otacheck': False, 'wifilog': False, 'free_memory': 58432, 'WifiVersion': 'AWS_Philips_AIR@79', 'ProductId': '7492f69e170b11eabc6802024953075e', 'DeviceId': 'f7191ce027f511ec86a5e2ba8ef26ff2', 'StatusType': 'status', 'ConnectType': 'Online', 'om': '1', 'pwr': '1', 'cl': False, 'aqil': 100, 'uil': '1', 'uaset': 'A', 'mode': 'AG', 'pm25': 3, 'iaql': 1, 'aqit': 4, 'aqit_ext': 0, 'tvoc': 1, 'ddp': '1', 'rddp': '1', 'err': 0, 'D0311F': 0, 'D03180': 255, 'D03R81': '000000000', 'D03182': 1, 'fltt1': 'A3', 'fltt2': 'none', 'fltsts0': 654, 'fltsts1': 4800, 'fltsts2': 0, 'filna': '0', 'filid': '0', 'flttotal0': 720, 'flttotal1': 4800, 'flttotal2': 65535}"

print(format_status(example_output))
