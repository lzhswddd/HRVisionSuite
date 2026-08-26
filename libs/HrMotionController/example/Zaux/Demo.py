import os
import sys

sys.path.append(os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller.components.zaux import *
from hrmotioncontroller import *

if __name__ == "__main__":
    import time
    # Example usage
    # 基础类
    zaux_motion = ZauxMotion([1])
    # ethercat总线
    # zaux_motion = ZauxEtherCatMotion([1])
    
    # ipaddr = '127.0.0.1'
    # zaux_motion.zaux.ZAux_OpenEth(ipaddr)
    
    # icomid = 0
    # zaux_motion.zaux.ZAux_OpenCom(icomid)
    
    # card_num = 0
    # zaux_motion.zaux.ZAux_OpenPci(card_num)
    
    # type = 5
    # pconnectstring = '5'
    # uims = 1000
    # zaux_motion.zaux.ZAux_FastOpen(type, pconnectstring, uims)
    
    axis = zaux_motion.get_axis(1)
    # 轴初始化
    axis.init(home_mode=HomeMode.Z_POSITIVE_HOME,
                pulse_equivalent=1000.0,
                acceleration=100.0,
                deceleration=100.0,
                sramp=20.0)
    
    # ethercat总线
    # axis.init(bas_filepath='ECAT初始化新.bas')
    
    #轴使能
    axis.enable()
    
    # 回零
    axis.home()
    
    while not axis.is_homed():
        print("Waiting for axes to home...")
        time.sleep(0.5)
        print(f"Current position: {axis.get_dpos()}")
    print("Axes are homed.")
    
    # 移动到绝对位置
    axis.move_absolute(1000.0, 100.0)