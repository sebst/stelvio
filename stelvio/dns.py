class StelvioDNS():
    def __init__(self):
        pass

    def create_record(self):
        return NotImplementedError("No DNS provider configured")

    def create_caa_record(self):
        return NotImplementedError("No DNS provider configured")