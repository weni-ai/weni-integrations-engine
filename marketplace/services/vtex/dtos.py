from dataclasses import dataclass


@dataclass
class APICredentials:
    domain: str
    app_key: str = ""
    app_token: str = ""
    use_io_proxy: bool = False
    project_uuid: str = ""

    def to_dict(self):
        result = {"domain": self.domain}
        if self.use_io_proxy:
            result["use_io_proxy"] = True
            result["project_uuid"] = self.project_uuid
        else:
            result["app_key"] = self.app_key
            result["app_token"] = self.app_token
        return result
