import yaml


class ConfigUtils:
    def __init__(self):
        self.config_file = 'config.yml'
        with open(self.config_file, 'r') as file:
            self.config = yaml.safe_load(file)

    def get_recent_projects(self):
        if self.config:
            return self.config['recent-projects']

    def get_phases(self):
        if self.config:
            return self.config['phases']

    def set_screen_size(self, height, width):
        if self.config:
            self.config['window-size'] = [height, width]
            with open(self.config_file, 'w') as file:
                yaml.dump(self.config, file)

    def get_screen_size(self):
        if self.config:
            return self.config['window-size']