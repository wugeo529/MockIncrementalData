CREATE TABLE s_signal_2_1_gps (
  imsi VARCHAR(255),
  satellite_num INT COMMENT '卫星编号，5，6，8，9，65535',
  position_num INT COMMENT '阵地编号，0，1，99，3',
  lon DECIMAL(20,8) COMMENT '经度',
  lat DECIMAL(20,8) COMMENT '纬度',
  insert_time DATETIME(6) COMMENT '输入时间',
  gps_time DATETIME(6) COMMENT '位置时间',
  means VARCHAR(255) COMMENT '手段,只有3',
  direction INT COMMENT '方向',
  alititude DECIMAL(20,8) COMMENT '高度',
  speed DECIMAL(20,8) COMMENT '速度',
  beam_num INT COMMENT '波束号，0~255',
  terminal_type_name VARCHAR(255) COMMENT '终端类型名称',
  satellite_name VARCHAR(255) COMMENT '卫星名称',
  region INT COMMENT '洋区',
  id INT NOT NULL,
  dumm_flag SMALLINT NOT NULL COMMENT '仿真标识，1：仿真数据，0真实数据',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE s_signal_2_1_ipsession (
  imsi VARCHAR(255),
  src_ip VARCHAR(255) COMMENT '源IP地址',
  dest_ip VARCHAR(255) COMMENT '目的IP地址',
  protocol INT COMMENT '协议类型，6，1，17，89',
  src_port INT COMMENT '源端口，0~65535',
  dest_port INT COMMENT '目的端口，0~65535',
  burst_time DATETIME(6) COMMENT '出联时间或突发时间',
  packet_len INT COMMENT '报文长度',
  id INT NOT NULL,
  dumm_flag SMALLINT NOT NULL COMMENT '仿真标识，1：仿真数据，0真实数据',
  insert_time DATETIME(6) COMMENT '输入时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE s_signal_2_1_target (
  imsi VARCHAR(255) COMMENT 'imsi',
  targetid VARCHAR(255) COMMENT '目标ID',
  level VARCHAR(255) COMMENT '等级',
  insert_time DATETIME(0) COMMENT '新增时间',
  imei VARCHAR(255) COMMENT 'IMEI',
  dumm_flag SMALLINT NOT NULL COMMENT '仿真标识，1：仿真数据，0真实数据',
  target_name VARCHAR(255) COMMENT '目标名称',
  target_category VARCHAR(255) COMMENT '目标类别',
  country VARCHAR(255) COMMENT '国家',
  _sim_id INT NOT NULL,
  PRIMARY KEY (_sim_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
