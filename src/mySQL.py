import MySQLdb
import sshtunnel
from configparser import ConfigParser

""" config = ConfigParser()
config.read('../angelman_viz_keys/config2.ini')
ssh_hostname = config['SSH']['ssh_hostname']
ssh_username = config['SSH']['ssh_username']
ssh_password = config['SSH']['ssh_password']
 """

sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

with sshtunnel.SSHTunnelForwarder(
    ('ssh.pythonanywhere.com'),
    ssh_username='anthonymoisan@yahoo.fr', ssh_password='Mmas&37813',
    remote_bind_address=('AnthonyMoisan.mysql.pythonanywhere-services.com', 3306)
) as tunnel:
    connection = MySQLdb.connect(
        user='AnthonyMoisan',
        passwd='Mmas&37813',
        host='127.0.0.1', port=tunnel.local_bind_port,
        db='AnthonyMoisan$AngelmanResult',
    )
    # Do stuff
    connection.close()  