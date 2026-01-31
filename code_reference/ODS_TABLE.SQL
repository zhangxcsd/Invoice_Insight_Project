--不分区，但按年度建表
--以 MySQL 5.7/8.0 作为SQL的主要语言标准
--发票数据导入时，要“先导入主表数据”，再“导入明细表数据”。发票主表或明细表若有删除，需要一并处理。
--兼顾了数据的可读性，字段设置时没有采用 TINYINT 类型

--提示。在注释中提到的方法或处理逻辑，需要在ETL 脚本（Python/Java）中处理，而不是依赖 SQL 函数
--发票主表的UUID，按照MD5（发票代码，发票号码，数电发票号码）。金税导出的数据中，括号、横杠常出现全角字符，必须统一清洗为半角后再做 MD5，否则会导致后续关联失败。
--处理时需主要要去除“”和“--”。如：MD5(CONCAT(IFNULL(fpdm,''), IFNULL(fphm,''), IFNULL(sdfphm,'')))或MD5(CONCAT(fpdm, fphm, sdfphm))。
--表ODS_VAT_INV_HEADER_FULL_2023的含义是，以2023年度的发票主表的汇总信息(包括红冲、作废等各类发票），对应的是金税系统导出Excel中“发票基础信息sheet”。
--在 ETL 阶段，尝试解析发票备注栏（bz），提取“对应正数发票代码:xxx 号码:xxx”的信息，并填入主表的 related_blue_invoice_uuid 字段

--以2023年度的发票主表的汇总信息为例，建表语句如下，其他年度可参照生成：

CREATE TABLE ODS_VAT_INV_HEADER_FULL_2023 (
    -- 系统字段（32位UUID）
    `header_uuid` CHAR(32) NOT NULL COMMENT '主表UUID（32位MD5）',	
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `created_by` VARCHAR(50) DEFAULT 'SYSTEM' COMMENT '创建人',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `updated_by` VARCHAR(50) DEFAULT 'SYSTEM' COMMENT '更新人',
    
    -- 数据质量字段
    `import_batch_id` VARCHAR(50) NOT NULL COMMENT '导入批次号', --数据导入时，由用户输入提供，导入时主表和明细表中分别记录
	`source_system` VARCHAR(50) DEFAULT '金税导出' COMMENT '数据来源',
	`source_file` VARCHAR(200) NOT NULL  COMMENT '数据来源文件', --用来描述发票是从哪个Excel文件中获取的
	`sync_status` VARCHAR(20) DEFAULT NULL COMMENT '同步状态:待同步/已同步/异常/导入作废',
	`clean_status`  VARCHAR(20) DEFAULT NULL COMMENT '清洗情况:明细缺失/...',--检查主表header_uuid是否都能在明细表找到，若不能则主表clean_status标记“明细缺失”
    
    -- 平账相关字段（新增/优化）
    `detail_total_amount` DECIMAL(18,2) DEFAULT NULL COMMENT '明细汇总金额',
    `is_balanced` ENUM('未校验','平账','不平账','差异可接受','强制通过') DEFAULT '未校验' COMMENT '平账状态',
    `balance_diff` DECIMAL(18,2) DEFAULT NULL` COMMENT '平账差异金额',
    `balance_tolerance` DECIMAL(18,2) DEFAULT 0.1 COMMENT '平账容忍度', --主表与明细表总额比对的差异值
    `balance_check_time` DATETIME COMMENT '平账校验时间',
    `balance_check_by` VARCHAR(50) DEFAULT 'SYSTEM' COMMENT '平账校验人',
    `balance_notes` TEXT COMMENT '平账备注',
    
	--红冲关联字段(红冲的单据要关联到对应的蓝单）
	`related_blue_invoice_uuid` CHAR(32) DEFAULT NULL COMMENT '红票对应原蓝票UUID',
    
	
	-- 业务原始字段（保持与EXCEL对齐）
    `fpdm` VARCHAR(30) COMMENT '发票代码',
    `fphm` VARCHAR(30) COMMENT '发票号码',
    `sdfphm` VARCHAR(50) COMMENT '数电发票号码',
    `xfsbh` VARCHAR(50) COMMENT '销方识别号',
    `xfmc` VARCHAR(500) COMMENT '销方名称',
    `gfsbh` VARCHAR(50) COMMENT '购方识别号',
    `gfmc` VARCHAR(500) COMMENT '购买方名称',
    `kprq` VARCHAR(25) COMMENT '开票日期（原始）',
    `invoice_date` DATE COMMENT '开票日期（标准化）',
    `invoice_time` TIME COMMENT '开票时间（标准化）',
    `je` DECIMAL(18,2) COMMENT '金额',
    `se` DECIMAL(18,2) COMMENT '税额',
    `jshj` DECIMAL(18,2) COMMENT '价税合计',
    `fply` VARCHAR(100) COMMENT '发票来源',
    `fppz` VARCHAR(100) COMMENT '发票票种',
    `fpzt` VARCHAR(50) COMMENT '发票状态',
    `sfzsfp` VARCHAR(10) COMMENT '是否正数发票',
    `fpfxdj` VARCHAR(50) COMMENT '发票风险等级',
    `kpr` VARCHAR(50) COMMENT '开票人',
    `bz` TEXT COMMENT '备注',
    
    -- 主键和外键
    PRIMARY KEY (`header_uuid`),
	
    
    -- 业务查询索引
    INDEX `idx_fpdm_fphm` (`fpdm`, `fphm`),
    INDEX `idx_xfsbh` (`xfsbh`),
    INDEX `idx_gfsbh` (`gfsbh`),
    INDEX `idx_invoice_date` (`invoice_date`),
    INDEX `idx_is_balanced` (`is_balanced`),
    INDEX `idx_clean_status` (`clean_status`),
	INDEX `idx_related_blue_uuid` (`related_blue_invoice_uuid`) COMMENT '优化红蓝票对冲关联查询',
    INDEX `idx_import_batch` (`import_batch_id`)
	   
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='发票基础信息表（ODS层）粒度：单张发票';




--表ODS_VAT_INV_DETAIL_FULL_2023的含义是，以2023年度的发票明细表的汇总信息(包括红冲、作废等各类发票的记录），对应的是金税系统导出Excel中“发票汇总表sheet”。
--权衡存储和性能，考虑到审计分析中需要对开票的产品按照日期进行筛选和分组。与主表一样，将标准化日期时间字段在明细表中进行了冗余，以优化查询性能。
--明细表的UUID，按照MD5（发票代码，发票号码，数电发票号码，发票明细的逻辑行号），处理时需主要要去除“”和“--”。如：MD5(CONCAT(IFNULL(fpdm,''), IFNULL(fphm,''), IFNULL(sdfphm,''),logic_line_no))或MD5(CONCAT(fpdm, fphm, sdfphm, logic_line_no))
--以2023年度的发票主表的汇总信息为例，建表语句如下，其他年度可参照生成：

CREATE TABLE ODS_VAT_INV_DETAIL_FULL_2023 (
    -- 系统字段
    `detail_uuid` CHAR(32) NOT NULL COMMENT '明细UUID（32位MD5）',
    `header_uuid` CHAR(32) NOT NULL COMMENT '主表关联UUID',
    `logic_line_no` INT NOT NULL COMMENT '逻辑行号',--明细表的 logic_line_no 必须在每一批次导入时重新按发票内部分组生成，严禁直接使用 Excel 原始序号，因为原始序号可能在多次导出、合并时发生变动
    `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',--子表字段更新时记录更新时间
    `updated_by` VARCHAR(50) DEFAULT 'SYSTEM' COMMENT '更新人',
    
    -- 数据质量字段
	`import_batch_id` VARCHAR(50) NOT NULL COMMENT '导入批次号', --数据导入时，由用户输入提供，导入时主表和明细表中分别记录
   	`source_system` VARCHAR(50) DEFAULT '金税导出' COMMENT '数据来源',
	`source_file` VARCHAR(200) NOT NULL  COMMENT '数据来源文件', --用来描述发票是从哪个Excel文件中获取的
	`sync_status` VARCHAR(20) DEFAULT NULL COMMENT '同步状态:待同步/已同步/异常/导入作废',
	`clean_status`  VARCHAR(20) DEFAULT NULL COMMENT '清洗情况:主表缺失/...', --检查明细表header_uuid是否都能在主表找到，若不能则明细表clean_status标记“主表缺失” 
	
    -- 业务原始字段
    `fpdm` VARCHAR(30) COMMENT '发票代码',
    `fphm` VARCHAR(30) COMMENT '发票号码',
    `sdfphm` VARCHAR(50) COMMENT '数电发票号码',
    `xfsbh` VARCHAR(50) COMMENT '销方识别号',
    `xfmc` VARCHAR(500) COMMENT '销方名称',
    `gfsbh` VARCHAR(50) COMMENT '购方识别号',
    `gfmc` VARCHAR(500) COMMENT '购买方名称',
	`kprq` VARCHAR(25) COMMENT '开票日期（原始）',
    `invoice_date` DATE COMMENT '开票日期（标准化）',
    `invoice_time` TIME COMMENT '开票时间（标准化）',
    
    -- 商品信息
	`ssflbm` VARCHAR(100) COMMENT '税收分类编码',
    `tdywlx` VARCHAR(200) COMMENT '特定业务类型',
    `hwlwmc` VARCHAR(1000) COMMENT '货物或应税劳务名称',
    `ggxh` VARCHAR(200) COMMENT '规格型号',
    `dw` VARCHAR(50) COMMENT '单位',
    `sl` DECIMAL(18,8) COMMENT '数量',
    `dj` DECIMAL(18,8) COMMENT '单价',
    `je` DECIMAL(18,2) COMMENT '金额',
    `slv` VARCHAR(20) COMMENT '税率',
    `se` DECIMAL(18,2) COMMENT '税额',
    `jshj` DECIMAL(18,2) COMMENT '价税合计',
    
    -- 其他字段
    `fply` VARCHAR(100) COMMENT '发票来源',
    `fppz` VARCHAR(100) COMMENT '发票票种',
    `fpzt` VARCHAR(50) COMMENT '发票状态',
    `sfzsfp` VARCHAR(10) COMMENT '是否正数发票',
    `fpfxdj` VARCHAR(50) COMMENT '发票风险等级',
    `kpr` VARCHAR(50) COMMENT '开票人',
    `bz` TEXT COMMENT '备注',
    
	--主键和索引
    PRIMARY KEY (`detail_uuid`),
	/*
	物理外键通常在业务系统（OLTP）中使用，若在明细表中定义了 CONSTRAINT fk_detail_header_2023。虽然保证了引用完整性，但在 ODS 层高频、大批量插入数据时，数据库每写一行明细都要去主表校验主键是否存在，这会产生巨大的 I/O 开销。因此，移除了物理外键。通过 ETL 程序（Python/Java）在逻辑上保证“先存主表、后存明细”，，而在数仓（OLAP/ODS）中通过索引来维持逻辑关联。
	
	CONSTRAINT fk_detail_header_2023  --因为是按年度分表，所以需要按年度创建对应的索引
        FOREIGN KEY (header_uuid) 
        REFERENCES ODS_VAT_INV_HEADER_FULL_2023(header_uuid) --建表时，要注意“年度”更新
	*/
    
    -- 索引（优化查询性能）
    INDEX `idx_header_uuid` (`header_uuid`),
    INDEX `idx_fpdm_fphm` (`fpdm`, `fphm`),
    INDEX `idx_ssflbm` (`ssflbm`),
    INDEX `idx_hwlwmc` (`hwlwmc`(100)),
    INDEX `idx_logic_line` (`header_uuid`, `logic_line_no`),
    INDEX `idx_clean_status` (`clean_status`),

    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='发票信息明细表（ODS层）粒度：发票明细行';