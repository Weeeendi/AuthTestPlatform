import configparser  

class param_struct(object):

    def __init__(self,section,key,value) -> None:
        self.section = section
        self.key = key
        self.value = value


class ini_object(object):

    object.file_name = "setting_config.ini"
    object.path = "resource/config/"

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()  
        self.file_name = object.file_name
        self.file_path = object.path
 
    def read_byKey(self,section:str,key):
        value = self.config.get(section,key)
        return value
            
  
    def wirte_byKey(self,section:str,key,value):
        # 添加section和对应的数据 
        self.config.set(section,key,value)
        # 保存到文件
        try:  
            with open(self.file_path + self.file_name, 'w') as configfile:  
                self.config.write(configfile)
        except OSError as e:
            print(e + self.file_path + self.file_name + "目标文件不存在")


class load_ini(ini_object):

    def __init__(self) -> None:
        super().__init__()
