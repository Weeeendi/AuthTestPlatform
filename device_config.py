# coding:utf-8
"""
设备配置管理模块
统一维护设备信息、页面索引、设备类型等映射关系
"""

from enum import Enum


class DeviceType(Enum):
    """设备类型定义"""
    DASHBOARD = 0
    CONTROLLER = 1
    BMS = 2
    IOT = 3
    SUB_BMS = 4
    DONGLE = 5


class ProtocolDeviceType(Enum):
    """协议中的设备类型定义"""
    DASHBOARD = 1
    CONTROLLER = 2
    BMS = 3
    IOT = 0
    SUB_BMS = 4
    DONGLE = 5


class DeviceConfig:
    """设备配置类
    
    统一管理所有设备的信息，包括：
    - 设备类型
    - 页面索引
    - 协议设备类型
    - DP数据组名
    - 在线状态属性名
    - 故障代码名
    """
    
    # 设备配置字典：{DeviceType: {配置信息}}
    DEVICES = {
        DeviceType.DASHBOARD: {
            'name': 'Dashboard',
            'page_index': 0,
            'protocol_type': ProtocolDeviceType.DASHBOARD.value,
            'dp_group': 'Dashboard_Dp_Data',
            'online_attr': 'dashBoardOnline',
            'error_code': 'dashboard_fault',
        },
        DeviceType.CONTROLLER: {
            'name': 'Controller',
            'page_index': 1,
            'protocol_type': ProtocolDeviceType.CONTROLLER.value,
            'dp_group': 'Controller_Dp_Data',
            'online_attr': 'controllerOnline',
            'error_code': 'controller_fault',
        },
        DeviceType.BMS: {
            'name': 'BMS',
            'page_index': 2,
            'protocol_type': ProtocolDeviceType.BMS.value,
            'dp_group': 'BMS_Dp_Data',
            'online_attr': 'BMSOnline',
            'error_code': 'bms_fault',
        },
        DeviceType.IOT: {
            'name': 'IoT',
            'page_index': 3,
            'protocol_type': ProtocolDeviceType.IOT.value,
            'dp_group': 'IoT_Dp_Data',
            'online_attr': 'IotOnline',
            'error_code': 'iot_fault',
        },
        DeviceType.SUB_BMS: {
            'name': 'SubBMS',
            'page_index': 4,
            'protocol_type': ProtocolDeviceType.SUB_BMS.value,
            'dp_group': 'SubBMS_Dp_Data',
            'online_attr': 'SubBMSOnline',
            'error_code': 'sub_bms_fault',
        },
        DeviceType.DONGLE: {
            'name': 'Dongle',
            'page_index': 5,
            'protocol_type': ProtocolDeviceType.DONGLE.value,
            'dp_group': None,  # Dongle 不需要 DP 数据组
            'online_attr': 'dongleOnline',
            'error_code': None,
        },
    }
    
    # 页面索引到设备类型的映射（用于快速查询）
    PAGE_TO_DEVICE = {config['page_index']: device_type 
                      for device_type, config in DEVICES.items()}
    
    # DP数据组到设备类型的映射
    DP_GROUP_TO_DEVICE = {config['dp_group']: device_type 
                          for device_type, config in DEVICES.items() 
                          if config['dp_group']}
    
    # 协议设备类型到DeviceType的映射（用于onStartOTA）
    PROTOCOL_TO_DEVICE = {config['protocol_type']: device_type 
                          for device_type, config in DEVICES.items()}
    
    @classmethod
    def get_device_by_page(cls, page_index):
        """根据页面索引获取设备类型"""
        return cls.PAGE_TO_DEVICE.get(page_index)
    
    @classmethod
    def get_device_by_dp_group(cls, dp_group):
        """根据 DP 数据组名获取设备类型"""
        return cls.DP_GROUP_TO_DEVICE.get(dp_group)
    
    @classmethod
    def get_device_by_protocol_type(cls, protocol_type):
        """根据协议设备类型获取 DeviceType"""
        return cls.PROTOCOL_TO_DEVICE.get(protocol_type)
    
    @classmethod
    def get_config(cls, device_type):
        """获取设备配置信息"""
        if isinstance(device_type, int):
            device_type = cls.get_device_by_page(device_type)
        return cls.DEVICES.get(device_type, {})
    
    @classmethod
    def get_page_index(cls, device_type):
        """获取设备的页面索引"""
        config = cls.get_config(device_type)
        return config.get('page_index', -1)
    
    @classmethod
    def get_protocol_type(cls, device_type):
        """获取设备的协议类型"""
        config = cls.get_config(device_type)
        return config.get('protocol_type', -1)
    
    @classmethod
    def get_online_attr(cls, device_type):
        """获取设备的在线状态属性名"""
        config = cls.get_config(device_type)
        return config.get('online_attr', '')
    
    @classmethod
    def get_dp_group(cls, device_type):
        """获取设备的 DP 数据组名"""
        config = cls.get_config(device_type)
        return config.get('dp_group', '')
    
    @classmethod
    def get_device_name(cls, device_type):
        """获取设备名称"""
        config = cls.get_config(device_type)
        return config.get('name', '')
    
    @classmethod
    def get_all_device_types(cls):
        """获取所有设备类型"""
        return list(cls.DEVICES.keys())
    
    @classmethod
    def get_all_dp_groups(cls):
        """获取所有 DP 数据组名"""
        return [config['dp_group'] for config in cls.DEVICES.values() if config['dp_group']]
    
    @classmethod
    def get_error_code(cls, device_type):
        """获取设备的故障代码"""
        config = cls.get_config(device_type)
        return config.get('error_code', '')
    
    @classmethod
    def is_dongle(cls, device_type):
        """检查是否为 Dongle 设备"""
        if isinstance(device_type, int):
            device_type = cls.get_device_by_page(device_type)
        return device_type == DeviceType.DONGLE
    
    @classmethod
    def get_page_type_list(cls):
        """获取兼容的 pageTypeList 格式（用于迁移）
        返回格式: [(page_index, protocol_type), ...]
        """
        return [(config['page_index'], config['protocol_type']) 
                for config in cls.DEVICES.values()]


# 为了向后兼容，导出旧的名称
DeviceList = [config['dp_group'] for config in DeviceConfig.DEVICES.values() if config['dp_group']]
ErrorCodeList = [config['error_code'] for config in DeviceConfig.DEVICES.values() if config['error_code']]
