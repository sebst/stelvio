from stelvio.dns import StelvioDns


class AwsDns(StelvioDns):
    def __init__(self):
        super().__init__()

    def create_record(self):
        # Implementation for creating a DNS record in AWS
        pass

    def create_caa_record(self):
        # Implementation for creating a CAA record in AWS
        pass