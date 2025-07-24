from stelvio.dns import StelvioDns


class CloudflareDns(StelvioDns):
    def __init__(self):
        super().__init__()

    def create_record(self):
        pass

    def create_caa_record(self):
        pass