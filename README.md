## verify that you have postgresql installed 
```
sudo apt install postgresql
```

## initialize the database and desired table
```
python3 database_setup.py
```

### run this for running the bot
```
python3 hr.py
```

## in /etc/systemd/system/hr.service
### change ubuntu user to your username
```
[Unit]
Description=HR Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/ubuntu/hr/hr.py
WorkingDirectory=/home/ubuntu/hr/
Restart=always
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

