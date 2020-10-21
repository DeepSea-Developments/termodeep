CREATE TABLE IF NOT EXISTS "records"
(
    [record_id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    [mac_address] NVARCHAR(17),

    [p_timestamp] TEXT,
    [p_barcode_type] INTEGER,
    [p_identification] NVARCHAR(160),
    [p_name] NVARCHAR(160),
    [p_last_name] NVARCHAR(160),
    [p_gender] NVARCHAR(1),
    [p_birth_date] TEXT,
    [p_expiration_date] TEXT,
    [p_blood_type] NVARCHAR(3),
    [p_extra_json] TEXT,
    [p_extra_txt] TEXT,
    [p_alert] INTEGER,

    [t_timestamp] TEXT,
    [t_temperature_mean] REAL,
    [t_temperature_median] REAL,
    [t_temperature_min] REAL,
    [t_temperature_max] REAL,
    [t_temperature_p10] REAL,
    [t_temperature_p20] REAL,
    [t_temperature_p30] REAL,
    [t_temperature_p40] REAL,
    [t_temperature_p50] REAL,
    [t_temperature_p60] REAL,
    [t_temperature_p70] REAL,
    [t_temperature_p80] REAL,
    [t_temperature_p90] REAL,
    [t_temperature_body] REAL,
    [t_image_thermal] BLOB,
    [t_image_rgb] BLOB,
    [t_alert] INTEGER
);