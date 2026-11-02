CREATE TABLE s_signal_2_1_gps (
  imsi varchar(255),
  satellite_num int4,
  position_num int4,
  lon float8,
  lat float8,
  insert_time timestamp(6),
  gps_time timestamp(6),
  means varchar(255),
  direction int4,
  alititude float8,
  speed float8,
  beam_num int4,
  terminal_type_name varchar(255),
  satellite_name varchar(255),
  region int4,
  id int4 NOT NULL,
  dumm_flag int2 NOT NULL,
  PRIMARY KEY (id)
);

COMMENT ON COLUMN s_signal_2_1_gps.satellite_num IS '卫星编号，5，6，8，9，65535';

COMMENT ON COLUMN s_signal_2_1_gps.position_num IS '阵地编号，0，1，99，3';

COMMENT ON COLUMN s_signal_2_1_gps.lon IS '经度';

COMMENT ON COLUMN s_signal_2_1_gps.lat IS '纬度';

COMMENT ON COLUMN s_signal_2_1_gps.insert_time IS '输入时间';

COMMENT ON COLUMN s_signal_2_1_gps.gps_time IS '位置时间';

COMMENT ON COLUMN s_signal_2_1_gps.means IS '手段,只有3';

COMMENT ON COLUMN s_signal_2_1_gps.direction IS '方向';

COMMENT ON COLUMN s_signal_2_1_gps.alititude IS '高度';

COMMENT ON COLUMN s_signal_2_1_gps.speed IS '速度';

COMMENT ON COLUMN s_signal_2_1_gps.beam_num IS '波束号，0~255';

COMMENT ON COLUMN s_signal_2_1_gps.terminal_type_name IS '终端类型名称';

COMMENT ON COLUMN s_signal_2_1_gps.satellite_name IS '卫星名称';

COMMENT ON COLUMN s_signal_2_1_gps.region IS '洋区';

COMMENT ON COLUMN s_signal_2_1_gps.dumm_flag IS '仿真标识，1：仿真数据，0真实数据';

CREATE TABLE s_signal_2_1_ipsession (
  imsi varchar(255),
  src_ip varchar(255),
  dest_ip varchar(255),
  protocol int4,
  src_port int4,
  dest_port int4,
  burst_time timestamp(6),
  packet_len int4,
  id int4 NOT NULL,
  dumm_flag int2 NOT NULL,
  insert_time timestamp(6)
);

COMMENT ON COLUMN s_signal_2_1_ipsession.src_ip IS '源IP地址';

COMMENT ON COLUMN s_signal_2_1_ipsession.dest_ip IS '目的IP地址';

COMMENT ON COLUMN s_signal_2_1_ipsession.protocol IS '协议类型，6，1，17，89';

COMMENT ON COLUMN s_signal_2_1_ipsession.src_port IS '源端口，0~65535';

COMMENT ON COLUMN s_signal_2_1_ipsession.dest_port IS '目的端口，0~65535';

COMMENT ON COLUMN s_signal_2_1_ipsession.burst_time IS '出联时间或突发时间';

COMMENT ON COLUMN s_signal_2_1_ipsession.packet_len IS '报文长度';

COMMENT ON COLUMN s_signal_2_1_ipsession.dumm_flag IS '仿真标识，1：仿真数据，0真实数据';

COMMENT ON COLUMN s_signal_2_1_ipsession.insert_time IS '输入时间';

CREATE TABLE s_signal_2_1_target (
  imsi varchar(255),
  targetid varchar(255),
  level varchar(255),
  insert_time timestamp(0),
  imei varchar(255),
  dumm_flag int2 NOT NULL,
  target_name varchar(255),
  target_category varchar(255),
  country varchar(255)
);

COMMENT ON COLUMN s_signal_2_1_target.imsi IS 'imsi';

COMMENT ON COLUMN s_signal_2_1_target.targetid IS '目标ID';

COMMENT ON COLUMN s_signal_2_1_target.level IS '等级';

COMMENT ON COLUMN s_signal_2_1_target.insert_time IS '新增时间';

COMMENT ON COLUMN s_signal_2_1_target.imei IS 'IMEI';

COMMENT ON COLUMN s_signal_2_1_target.dumm_flag IS '仿真标识，1：仿真数据，0真实数据';

COMMENT ON COLUMN s_signal_2_1_target.target_name IS '目标名称';

COMMENT ON COLUMN s_signal_2_1_target.target_category IS '目标类别';

COMMENT ON COLUMN s_signal_2_1_target.country IS '国家';
