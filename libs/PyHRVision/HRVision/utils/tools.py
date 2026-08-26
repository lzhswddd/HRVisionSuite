import socket
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import threading
import time
import datetime
import psutil

def scan_port(port):
    """
    扫描单个端口是否可用
    :param port: 要扫描的端口
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_:
        result = socket_.connect_ex(('127.0.0.1', port))
        # print(f"Scanning port {port}...")  # 打印扫描进度
        if result != 0:  # 如果返回值不为0，表示端口可用
            return True
    return False

def get_local_ip() -> str:
    """
    获取本地IP地址
    :return: 本地IP地址
    """
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def save_to_xml(data, file_path):
    """
    将数据保存为 XML 文件
    :param data: 要保存的数据（字典或列表）
    :param file_path: 保存的 XML 文件路径
    """
    def build_xml_element(parent, key, value):
        """
        递归构建 XML 元素
        :param parent: 父元素
        :param key: 当前键
        :param value: 当前值
        """
        if isinstance(value, dict):
            # 如果值是字典，递归创建子元素
            element = ET.SubElement(parent, key)
            for sub_key, sub_value in value.items():
                build_xml_element(element, sub_key, sub_value)
        elif isinstance(value, list):
            # 如果值是列表，为每个元素创建子元素
            for item in value:
                item_element = ET.SubElement(parent, key)
                build_xml_element(item_element, "item", item)
        else:
            # 如果值是基本类型，直接创建子元素
            element = ET.SubElement(parent, key)
            element.text = str(value)

    # 创建根元素
    root = ET.Element("root")
    for key, value in data.items():
        build_xml_element(root, key, value)

    # 创建 XML 树并保存到文件
    # tree = ET.ElementTree(root)
    # tree.write(file_path, encoding="utf-8", xml_declaration=True)
    
    # 格式化输出
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ")

    # 保存到文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def read_from_xml(file_path):
    """
    从 XML 文件读取数据
    :param file_path: XML 文件路径
    :return: 读取的数据（字典）
    """
    def parse_xml_element(element):
        """
        递归解析 XML 元素
        :param element: 当前 XML 元素
        :return: 解析后的数据
        """
        if len(element) == 0:
            # 如果没有子元素，返回文本内容
            return element.text
        elif all(child.tag == "item" for child in element):
            # 如果所有子元素都是 "item"，返回列表
            return [parse_xml_element(child) for child in element]
        else:
            # 否则返回字典
            return {child.tag: parse_xml_element(child) for child in element}

    # 解析 XML 文件
    tree = ET.parse(file_path)
    root = tree.getroot()
    return {child.tag: parse_xml_element(child) for child in root}

def delay_execute(func, delay, *args, **kwargs):
    """
    延迟执行函数
    :param func: 要执行的函数
    :param delay: 延迟时间（秒）
    :param args: 传递给函数的位置参数
    :param kwargs: 传递给函数的关键字参数
    """
    def wrapper(*args, **kwargs):
        threading.Event().wait(delay)
        func(*args, **kwargs)
        
    thread = threading.Thread(target=wrapper, args=args, kwargs=kwargs)
    thread.start()

def delay(delay_time: int):
    """
    延迟
    :param delay_time: 延迟时间（秒）
    """
    threading.Event().wait(delay_time)

def get_current_time(format='%Y-%m-%d %H:%M:%S.%f') -> str:
    """
    获取当前时间
    :param format: 时间格式
    :return: 格式化后的当前时间字符串
    """
    return datetime.datetime.now().strftime(format)

def get_current_savetime(format='%Y-%m-%d %H_%M_%S_%f', last=-3) -> str:
    """
    获取当前时间并格式化为保存文件的时间格式
    :param format: 时间格式
    :return: 格式化后的当前时间字符串
    """
    return get_current_time(format)[:last]

def async_run(func, *args, wait=False, daemon=False, **kwargs):
    """
    异步执行函数
    :param func: 要执行的函数
    :param args: 传递给函数的位置参数
    :param daemon: 是否为守护线程
    :param kwargs: 传递给函数的关键字参数
    """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
    thread.start()
    if wait:
        thread.join()

class TimerCounter:
    """
    计时类，用于测量代码块的执行时间
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """
        开始计时
        """
        self.start_time = time.time()

    def stop(self):
        """
        停止计时
        """
        self.end_time = time.time()

    def elapsed(self) -> float:
        """
        获取计时的时间间隔
        :return: 时间间隔（秒）
        """
        if self.start_time is None or self.end_time is None:
            raise ValueError("Timer has not been started or stopped.")
        return self.end_time - self.start_time
    
    def elapsed_ms(self) -> float:
        """
        获取计时的时间间隔（毫秒）
        :return: 时间间隔（毫秒）
        """
        return self.elapsed() * 1000

    @staticmethod
    def record(func, callback=None):
        """
        装饰器，用于记录函数的执行时间
        :param func: 要记录的函数
        :param callback: 回调函数，接收函数名和执行时间
        :return: 包装后的函数
        """
        def wrapper(*args, **kwargs):
            timer = TimerCounter()
            timer.start()
            result = func(*args, **kwargs)
            timer.stop()
            if callback is not None:
                callback(func.__name__, timer.elapsed_ms())
            return result
        return wrapper

class TimerOut(TimerCounter):
    def __init__(self, timeOut: float):
        """
        超时装饰器
        :param timeOut: 超时时间（秒）
        """
        self.timeOut = timeOut
    
    def set_timeout(self, timeOut: float):
        """
        设置超时时间
        :param timeOut: 超时时间（秒）
        """
        self.timeOut = timeOut
        
    def is_timeout(self):
        """
        检查是否超时
        :return: 是否超时
        """
        return self.elapsed() > self.timeOut
    
    @classmethod
    def gen(cls, func, timeout: float, is_raise=True):
        """
        装饰器，用于记录函数的执行时间并检查超时
        :param func: 要记录的函数
        :return: 包装后的函数
        """
        def wrapper(*args, **kwargs):
            timeout_event = threading.Event()
            result = None
            def inner():
                nonlocal result
                result = func(*args, **kwargs)
                timeout_event.set()
            threading.Thread(target=inner, daemon=True).start()
            ret = timeout_event.wait(timeout)
            if ret:
                # 如果函数在超时时间内执行完毕
                return result
            else:
                # 如果函数超时
                if is_raise:
                    raise TimeoutError(f"Function '{func.__name__}' timed out after {timeout} seconds.")
                else:
                    return None
        return wrapper

def set_program_high_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.HIGH_PRIORITY_CLASS)
    
def set_program_normal_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.NORMAL_PRIORITY_CLASS)
    
def set_program_low_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.IDLE_PRIORITY_CLASS)
    
def set_program_realtime_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.REALTIME_PRIORITY_CLASS)
    
def set_above_normal_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
    
def set_below_normal_priority():
    psutil.Process(psutil.Process().pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    
def set_program_priority(priority):
    """
    设置程序的优先级
    :param priority: 优先级，可以是 'high', 'normal', 'low', 'realtime', 'above_normal', 'below_normal'
    """
    priority_map = {
        'high': psutil.HIGH_PRIORITY_CLASS,
        'normal': psutil.NORMAL_PRIORITY_CLASS,
        'low': psutil.IDLE_PRIORITY_CLASS,
        'realtime': psutil.REALTIME_PRIORITY_CLASS,
        'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
        'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS
    }
    
    if priority in priority_map:
        psutil.Process(psutil.Process().pid).nice(priority_map[priority])
    else:
        raise ValueError(f"Unknown priority: {priority}")
    
    
if __name__ == "__main__":
    # def test_function(name, cast_time):
    #     print(f"Function '{name}' executed in {cast_time:.2f} ms")
    # print(TimerCounter.record(scan_port, callback=test_function)(3124))
    try:
        def test_function(name):
            time.sleep(1)
            return name
        print(TimerOut.gen(test_function, timeout=2)('test'))
    except TimeoutError as e:
        print(e)
