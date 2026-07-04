from dataclasses import dataclass, field
from PySide6.QtCore import QSettings


@dataclass
class ViewerState:
    cli_path: str = ""
    socket_path: str = ""
    send_in_hex: bool = False
    eol_index: int = 0
    mode_index: int = 0
    udp_bind_host: str = "0.0.0.0"
    udp_bind_port: str = "19000"
    udp_target_host: str = "127.0.0.1"
    udp_target_port: str = "19085"
    tcp_cli_host: str = "127.0.0.1"
    tcp_cli_port: str = "19085"
    tcp_srv_host: str = "0.0.0.0"
    tcp_srv_port: str = "19085"
    tcp_prx_listen_host: str = "127.0.0.1"
    tcp_prx_listen_port: str = "19000"
    tcp_prx_target_host: str = "127.0.0.1"
    tcp_prx_target_port: str = "19085"
    ser_port: str = "/dev/ttyUSB0"
    ser_baud: str = "115200"
    decoder_index: int = 0
    dec_fixed_size: int = 16
    dec_delim: str = "0A"
    dec_delim_inc: bool = False
    dec_len_size: str = "2"
    dec_len_endian: str = "big"
    dec_len_inc_hdr: bool = False
    log_file: str = "capture.jsonl"
    log_enabled: bool = False


class ViewerSettingsManager:
    def __init__(self, org: str, app: str):
        self._settings = QSettings(org, app)

    def load(self, defaults: ViewerState) -> ViewerState:
        s = self._settings
        return ViewerState(
            cli_path=s.value("cli_path", defaults.cli_path),
            socket_path=s.value("socket_path", defaults.socket_path),
            send_in_hex=s.value("send_in_hex", "false") == "true",
            eol_index=int(s.value("eol_index", defaults.eol_index)),
            mode_index=int(s.value("mode_index", defaults.mode_index)),
            udp_bind_host=s.value("udp_bind_host", defaults.udp_bind_host),
            udp_bind_port=s.value("udp_bind_port", defaults.udp_bind_port),
            udp_target_host=s.value("udp_target_host", defaults.udp_target_host),
            udp_target_port=s.value("udp_target_port", defaults.udp_target_port),
            tcp_cli_host=s.value("tcp_cli_host", defaults.tcp_cli_host),
            tcp_cli_port=s.value("tcp_cli_port", defaults.tcp_cli_port),
            tcp_srv_host=s.value("tcp_srv_host", defaults.tcp_srv_host),
            tcp_srv_port=s.value("tcp_srv_port", defaults.tcp_srv_port),
            tcp_prx_listen_host=s.value("tcp_prx_listen_host", defaults.tcp_prx_listen_host),
            tcp_prx_listen_port=s.value("tcp_prx_listen_port", defaults.tcp_prx_listen_port),
            tcp_prx_target_host=s.value("tcp_prx_target_host", defaults.tcp_prx_target_host),
            tcp_prx_target_port=s.value("tcp_prx_target_port", defaults.tcp_prx_target_port),
            ser_port=s.value("ser_port", defaults.ser_port),
            ser_baud=s.value("ser_baud", defaults.ser_baud),
            decoder_index=int(s.value("decoder_index", defaults.decoder_index)),
            dec_fixed_size=int(s.value("dec_fixed_size", defaults.dec_fixed_size)),
            dec_delim=s.value("dec_delim", defaults.dec_delim),
            dec_delim_inc=s.value("dec_delim_inc", "false") == "true",
            dec_len_size=s.value("dec_len_size", defaults.dec_len_size),
            dec_len_endian=s.value("dec_len_endian", defaults.dec_len_endian),
            dec_len_inc_hdr=s.value("dec_len_inc_hdr", "false") == "true",
            log_file=s.value("log_file", defaults.log_file),
            log_enabled=s.value("log_enabled", "false") == "true",
        )

    def save(self, state: ViewerState) -> None:
        s = self._settings
        s.setValue("cli_path", state.cli_path)
        s.setValue("socket_path", state.socket_path)
        s.setValue("send_in_hex", "true" if state.send_in_hex else "false")
        s.setValue("eol_index", state.eol_index)
        s.setValue("mode_index", state.mode_index)
        s.setValue("udp_bind_host", state.udp_bind_host)
        s.setValue("udp_bind_port", state.udp_bind_port)
        s.setValue("udp_target_host", state.udp_target_host)
        s.setValue("udp_target_port", state.udp_target_port)
        s.setValue("tcp_cli_host", state.tcp_cli_host)
        s.setValue("tcp_cli_port", state.tcp_cli_port)
        s.setValue("tcp_srv_host", state.tcp_srv_host)
        s.setValue("tcp_srv_port", state.tcp_srv_port)
        s.setValue("tcp_prx_listen_host", state.tcp_prx_listen_host)
        s.setValue("tcp_prx_listen_port", state.tcp_prx_listen_port)
        s.setValue("tcp_prx_target_host", state.tcp_prx_target_host)
        s.setValue("tcp_prx_target_port", state.tcp_prx_target_port)
        s.setValue("ser_port", state.ser_port)
        s.setValue("ser_baud", state.ser_baud)
        s.setValue("decoder_index", state.decoder_index)
        s.setValue("dec_fixed_size", state.dec_fixed_size)
        s.setValue("dec_delim", state.dec_delim)
        s.setValue("dec_delim_inc", "true" if state.dec_delim_inc else "false")
        s.setValue("dec_len_size", state.dec_len_size)
        s.setValue("dec_len_endian", state.dec_len_endian)
        s.setValue("dec_len_inc_hdr", "true" if state.dec_len_inc_hdr else "false")
        s.setValue("log_file", state.log_file)
        s.setValue("log_enabled", "true" if state.log_enabled else "false")
