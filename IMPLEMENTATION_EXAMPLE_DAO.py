"""
实际集成示例：使用 DAO 层重写关键函数

这个文件展示了如何将现有的 VAT_Invoice_Processor 函数迁移到 DAO 层。
这些是伪代码 + 实际代码的混合，用于指导实际集成。

注意：这是独立的示例文件，不会影响主程序运行。
"""

# ============================================================================
# 示例 1：在 VATAuditPipeline 类中初始化 DAO
# ============================================================================

class VATAuditPipeline:
    """发票审计流水线 - 使用 DAO 层的版本"""

    def __init__(self, config_obj, base_dir: str):
        """初始化流水线，创建数据库连接和 DAO 对象。"""
        from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO, ODSHeaderDAO
        
        self.config = config_obj
        self.base_dir = base_dir
        
        # ... 其他初始化 ...
        
        # 【新增】初始化数据库连接
        db_path = os.path.join(base_dir, 'Database', 'vat_audit.sqlite')
        self.db = DatabaseConnection(db_path, timeout=30.0)
        self.db.pragma_optimize(mode='wal')  # 启用 WAL 优化
        
        # 【新增】初始化 DAO 对象
        business_tag = self.config.get('business', 'business_tag', default='VAT_INV')
        self.ods_detail_dao = ODSDetailDAO(self.db, business_tag)
        self.ods_header_dao = ODSHeaderDAO(self.db, business_tag)
        
        logger.info(f"✓ 数据库连接已初始化: {db_path}")
        logger.info(f"✓ DAO 对象已创建 (business_tag={business_tag})")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源，关闭数据库连接。"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            logger.info("✓ 数据库连接已关闭")


# ============================================================================
# 示例 2：使用 DAO 替代 _prepare_ods_tables
# ============================================================================

def _prepare_ods_tables_dao_version(self, detail_columns, header_columns, summary_columns):
    """
    创建或重置 ODS 层表结构 - 使用 DAO 层版本。
    
    原版本代码（使用直接 sqlite3）：
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS ODS_{BUSINESS_TAG}_TEMP_TRANSIT")
        conn.commit()
        pd.DataFrame(columns=list(detail_columns)).to_sql(...)
    
    DAO 层版本：直接使用 DAO 方法删除表。
    """
    try:
        with self.db.transaction():
            # 使用 DAO 的 drop_table 方法
            logger.info("清空 ODS 表...")
            self.ods_detail_dao.drop_table()
            self.ods_header_dao.drop_table()
            
            # 创建空表（仍使用 pandas to_sql 以便快速建立表结构）
            import pandas as pd
            pd.DataFrame(columns=list(detail_columns)).to_sql(
                f"ODS_{self.config.get('business', 'business_tag', default='VAT_INV')}_DETAIL",
                self.db.connect(),
                if_exists='replace',
                index=False,
                method='multi'
            )
            pd.DataFrame(columns=list(header_columns)).to_sql(
                f"ODS_{self.config.get('business', 'business_tag', default='VAT_INV')}_HEADER",
                self.db.connect(),
                if_exists='replace',
                index=False,
                method='multi'
            )
            
            logger.info("✓ ODS 表已准备就绪")
    except Exception as e:
        logger.error(f"✗ ODS 表准备失败: {e}")
        raise


# ============================================================================
# 示例 3：使用 DAO 替代 process_dwd（关键示例）
# ============================================================================

def process_dwd_dao_version(self, process_time: str):
    """
    处理 DWD（数据仓库详细层）和生成 LEDGER 台账 - 使用 DAO 层版本。
    
    原版本代码（使用直接 sqlite3）：
        yrs = pd.read_sql(
            f"SELECT DISTINCT 开票年份 as y FROM ODS_{BUSINESS_TAG}_DETAIL WHERE 开票年份 IS NOT NULL",
            conn
        )['y'].dropna().tolist()
        
        for yr in yrs:
            df = pd.read_sql(
                f"SELECT * FROM ODS_{BUSINESS_TAG}_DETAIL WHERE 开票年份={yr}",  # ❌ SQL 注入风险
                conn
            )
    
    DAO 层版本：使用参数化查询通过 DAO。
    """
    from vat_audit_pipeline.utils.database import LedgerDAO
    import pandas as pd
    
    logger.info("处理 DWD 层，生成 LEDGER 台账...")
    ledger_rows = []
    duplicates_detail = []
    duplicates_header = []
    
    business_tag = self.config.get('business', 'business_tag', default='VAT_INV')
    
    try:
        # ========== 处理明细层 ==========
        
        # 【使用 DAO】获取所有年份（参数化查询）
        years = self.ods_detail_dao.get_distinct_years()
        logger.info(f"发现 {len(years)} 个年度: {years}")
        
        detail_cols_needed = [
            '发票代码', '发票号码', '数电发票号码', '销方识别号', '销方名称',
            '购方识别号', '购买方名称', '开票日期', '税收分类编码', '特定业务类型',
            '货物或应税劳务名称', '规格型号', '单位', '数量', '单价', '金额',
            '税率', '税率_数值', '税额', '价税合计', '发票来源', '发票票种',
            '发票状态', '是否正数发票', '发票风险等级', '开票人', '备注'
        ]
        
        detail_dedup_subset = [
            '发票代码', '发票号码', '数电发票号码', '开票日期', '货物或应税劳务名称',
            '数量', '单价', '金额', '税额', '发票票种', '发票状态', '开票人', '备注'
        ]
        
        for i, year in enumerate(years, start=1):
            if not (year and str(year).isdigit()):
                continue
            
            logger.info(f"[{i}/{len(years)}] 处理 {year} 年度明细...")
            
            # 【使用 DAO】按年份查询明细（参数化查询）
            detail_records = self.ods_detail_dao.find_by_year(str(year))
            
            # 转换为 DataFrame
            df = pd.DataFrame([dict(row) for row in detail_records])
            
            if df.empty:
                logger.warning(f"  ⚠ {year} 年度无数据")
                continue
            
            rows_before = len(df)
            
            # 执行业务逻辑（去重、筛选列）
            dedup_keys = [c for c in detail_dedup_subset if c in df.columns]
            if dedup_keys:
                mask_dup = df.duplicated(subset=dedup_keys, keep='first')
            else:
                mask_dup = df.duplicated(keep='first')
            
            df_dedup = df[~mask_dup].copy()
            df_dups = df[mask_dup].copy()
            
            rows_after = len(df_dedup)
            rows_dropped = rows_before - rows_after
            
            # 保存重复记录用于审计
            if not df_dups.empty:
                if 'AUDIT_IMPORT_TIME' not in df_dups.columns:
                    df_dups['AUDIT_IMPORT_TIME'] = process_time
                df_dups['DEDUP_CAPTURE_TIME'] = process_time
                duplicates_detail.append(df_dups)
            
            # 【使用 DAO】写入 LEDGER 表
            cols_present = [c for c in detail_cols_needed if c in df_dedup.columns]
            df_out = df_dedup[cols_present].copy()
            
            ledger_dao = LedgerDAO(self.db, business_tag, str(year), 'detail')
            df_out.to_sql(
                ledger_dao.table_name,
                self.db.connect(),
                if_exists='replace',
                index=False
            )
            
            logger.info(f"  ✓ 明细: {rows_before} -> {rows_after} 条 (去重 {rows_dropped} 条)")
            
            ledger_rows.append({
                'type': 'detail',
                'year': year,
                'rows_before': rows_before,
                'rows_after': rows_after,
                'rows_dropped': rows_dropped,
                'cols': ','.join(cols_present)
            })
        
        # ========== 处理表头层（代码类似） ==========
        
        years_hdr = self.ods_header_dao.get_distinct_years()
        
        header_cols_needed = [
            '发票代码', '发票号码', '数电发票号码', '销方识别号', '销方名称',
            '购方识别号', '购买方名称', '开票日期', '金额', '税率', '税率_数值',
            '税额', '价税合计', '发票来源', '发票票种', '发票状态', '是否正数发票',
            '发票风险等级', '开票人', '备注'
        ]
        
        header_dedup_subset = ['发票代码', '发票号码', '数电发票号码']
        
        for i, year in enumerate(years_hdr, start=1):
            if not (year and str(year).isdigit()):
                continue
            
            logger.info(f"[{i}/{len(years_hdr)}] 处理 {year} 年度表头...")
            
            # 【使用 DAO】按年份查询表头
            header_records = self.ods_header_dao.find_by_year(str(year))
            df = pd.DataFrame([dict(row) for row in header_records])
            
            if df.empty:
                continue
            
            rows_before = len(df)
            
            dedup_keys = [c for c in header_dedup_subset if c in df.columns]
            if dedup_keys:
                mask_dup = df.duplicated(subset=dedup_keys, keep='first')
            else:
                mask_dup = df.duplicated(keep='first')
            
            df_dedup = df[~mask_dup].copy()
            df_dups = df[mask_dup].copy()
            rows_after = len(df_dedup)
            
            if not df_dups.empty:
                if 'AUDIT_IMPORT_TIME' not in df_dups.columns:
                    df_dups['AUDIT_IMPORT_TIME'] = process_time
                df_dups['DEDUP_CAPTURE_TIME'] = process_time
                duplicates_header.append(df_dups)
            
            # 【使用 DAO】写入 LEDGER 表
            cols_present = [c for c in header_cols_needed if c in df_dedup.columns]
            df_out = df_dedup[cols_present].copy()
            
            ledger_dao = LedgerDAO(self.db, business_tag, str(year), 'header')
            df_out.to_sql(
                ledger_dao.table_name,
                self.db.connect(),
                if_exists='replace',
                index=False
            )
            
            logger.info(f"  ✓ 表头: {rows_before} -> {rows_after} 条")
            
            ledger_rows.append({
                'type': 'header',
                'year': year,
                'rows_before': rows_before,
                'rows_after': rows_after,
                'rows_dropped': rows_before - rows_after,
                'cols': ','.join(cols_present)
            })
        
        logger.info(f"✓ DWD 处理完成，共 {len(ledger_rows)} 个 LEDGER 表")
        
    except Exception as e:
        logger.error(f"✗ DWD 处理失败: {e}")
        raise
    
    return ledger_rows, duplicates_detail, duplicates_header


# ============================================================================
# 示例 4：在 merge_ods_to_db 中使用事务
# ============================================================================

def merge_ods_to_db_dao_version(self, csv_files_by_table: dict, process_time: str):
    """
    将临时 CSV 合并到 SQLite - 使用 DAO 层的事务管理。
    
    原版本代码：
        cursor.execute('BEGIN IMMEDIATE')
        try:
            for csv_file in csv_files:
                df = pd.read_csv(csv_file)
                df.to_sql(table_name, conn, if_exists='append', ...)
            conn.commit()
        except Exception:
            conn.rollback()
    
    DAO 层版本：使用 db.transaction() 上下文管理器。
    """
    logger.info("合并临时 CSV 到 SQLite...")
    
    try:
        # 【使用 DAO】事务管理
        with self.db.transaction():
            for table_name, csv_files in csv_files_by_table.items():
                logger.info(f"合并 {table_name}: {len(csv_files)} 个文件...")
                
                for csv_file in csv_files:
                    try:
                        import pandas as pd
                        df = pd.read_csv(csv_file, encoding='utf-8')
                        
                        # 使用 pandas 的 to_sql（内部会使用连接）
                        df.to_sql(
                            table_name,
                            self.db.connect(),
                            if_exists='append',
                            index=False,
                            method='multi',
                            chunksize=1000
                        )
                        
                        logger.debug(f"  ✓ {csv_file} 已合并到 {table_name}")
                    
                    except Exception as e:
                        logger.error(f"  ✗ 合并 {csv_file} 失败: {e}")
                        raise  # 在事务中抛出异常会触发自动回滚
        
        logger.info("✓ 所有 CSV 已合并到数据库")
    
    except Exception as e:
        logger.error(f"✗ 合并操作失败（已自动回滚）: {e}")
        raise


# ============================================================================
# 示例 5：使用 DAO 执行分析查询（ADS 层）
# ============================================================================

def detect_tax_anomalies_dao_version(self, process_time: str):
    """
    检测异常税率 - 使用 DAO 层。
    
    示例：查询所有税率异常的发票（本应为 13% 但实际为其他值）。
    """
    from vat_audit_pipeline.utils.database import OADSAnalyticsDAO
    import pandas as pd
    
    logger.info("检测异常税率...")
    
    business_tag = self.config.get('business', 'business_tag', default='VAT_INV')
    
    try:
        # 获取所有年份
        years = self.ods_detail_dao.get_distinct_years()
        
        anomalies = []
        
        for year in years:
            if not (year and str(year).isdigit()):
                continue
            
            logger.info(f"检查 {year} 年度异常税率...")
            
            # 【使用 DAO】查询该年份所有明细
            details = self.ods_detail_dao.find_by_year(str(year))
            df = pd.DataFrame([dict(row) for row in details])
            
            if df.empty:
                continue
            
            # 业务逻辑：检测异常税率
            # 例如：标准商品税率应为 13%，特殊商品为 6%
            standard_rate = 0.13
            special_rate = 0.06
            expected_rates = {standard_rate, special_rate}
            
            # 标准化税率列
            df['税率_数值'] = pd.to_numeric(df.get('税率_数值', 0), errors='coerce')
            
            # 找出异常税率（不在预期值中）
            mask_anomaly = ~df['税率_数值'].isin(expected_rates)
            df_anomaly = df[mask_anomaly].copy()
            
            if not df_anomaly.empty:
                df_anomaly['异常类型'] = 'UNEXPECTED_TAX_RATE'
                df_anomaly['检测时间'] = process_time
                df_anomaly['检测年份'] = year
                
                # 保存到分析结果表
                ads_dao = OADSAnalyticsDAO(
                    self.db,
                    f"ADS_{business_tag}_TAX_ANOMALY"
                )
                
                # 写入异常记录
                df_anomaly.to_sql(
                    ads_dao.table_name,
                    self.db.connect(),
                    if_exists='append',
                    index=False
                )
                
                anomalies.append({
                    'year': year,
                    'count': len(df_anomaly),
                    'records': df_anomaly
                })
                
                logger.info(f"  ⚠ {year} 年发现 {len(df_anomaly)} 条异常税率")
        
        logger.info(f"✓ 异常检测完成，共 {len(anomalies)} 个年度有异常")
        return anomalies
    
    except Exception as e:
        logger.error(f"✗ 异常检测失败: {e}")
        raise


# ============================================================================
# 示例 6：使用 DAO 进行数据验证和统计
# ============================================================================

def generate_data_quality_report(self, process_time: str) -> dict:
    """
    生成数据质量报告 - 使用 DAO 层的各种查询方法。
    
    包括：
    - 各表的行数统计
    - 各年份的数据分布
    - 异常数据的摘要
    """
    logger.info("生成数据质量报告...")
    
    business_tag = self.config.get('business', 'business_tag', default='VAT_INV')
    report = {
        'timestamp': process_time,
        'ods_summary': {},
        'ledger_summary': {},
        'data_quality_issues': []
    }
    
    try:
        # ========== ODS 层统计 ==========
        
        # 【使用 DAO】统计 ODS 明细表
        detail_count = self.ods_detail_dao.count()
        report['ods_summary']['detail_total'] = detail_count
        
        detail_by_year = {}
        for year in self.ods_detail_dao.get_distinct_years():
            count = self.ods_detail_dao.count_by_year(str(year))
            detail_by_year[str(year)] = count
        report['ods_summary']['detail_by_year'] = detail_by_year
        
        # 【使用 DAO】统计 ODS 表头表
        header_count = self.ods_header_dao.count()
        report['ods_summary']['header_total'] = header_count
        
        header_by_year = {}
        for year in self.ods_header_dao.get_distinct_years():
            count = self.ods_header_dao.count_by_year(str(year))
            header_by_year[str(year)] = count
        report['ods_summary']['header_by_year'] = header_by_year
        
        # ========== LEDGER 层统计 ==========
        
        from vat_audit_pipeline.utils.database import LedgerDAO
        
        for year in self.ods_detail_dao.get_distinct_years():
            if not (year and str(year).isdigit()):
                continue
            
            # 统计明细 LEDGER
            ledger_detail_dao = LedgerDAO(self.db, business_tag, str(year), 'detail')
            if ledger_detail_dao.table_exists():
                detail_ledger_count = ledger_detail_dao.count()
                report['ledger_summary'][f'{year}_detail'] = detail_ledger_count
            
            # 统计表头 LEDGER
            ledger_header_dao = LedgerDAO(self.db, business_tag, str(year), 'header')
            if ledger_header_dao.table_exists():
                header_ledger_count = ledger_header_dao.count()
                report['ledger_summary'][f'{year}_header'] = header_ledger_count
        
        # ========== 数据质量检查 ==========
        
        # 检查：明细表是否为空
        if detail_count == 0:
            report['data_quality_issues'].append({
                'level': 'ERROR',
                'message': 'ODS 明细表为空'
            })
        
        # 检查：表头表是否为空
        if header_count == 0:
            report['data_quality_issues'].append({
                'level': 'ERROR',
                'message': 'ODS 表头表为空'
            })
        
        # 检查：明细和表头的记录数比例
        if header_count > 0:
            ratio = detail_count / header_count
            if ratio < 1.0 or ratio > 100.0:
                report['data_quality_issues'].append({
                    'level': 'WARNING',
                    'message': f'明细/表头比例异常: {ratio:.1f}'
                })
        
        logger.info(f"✓ 数据质量报告已生成")
        logger.info(f"  - ODS 明细: {detail_count} 条")
        logger.info(f"  - ODS 表头: {header_count} 条")
        logger.info(f"  - 质量问题: {len(report['data_quality_issues'])} 个")
        
        return report
    
    except Exception as e:
        logger.error(f"✗ 报告生成失败: {e}")
        raise


if __name__ == '__main__':
    print("""
    实际集成示例
    ===========
    
    本文件包含了以下示例函数的 DAO 层版本：
    
    1. __init__ / __exit__
       - 初始化 DatabaseConnection
       - 初始化 DAO 对象
    
    2. _prepare_ods_tables_dao_version
       - 使用 DAO 的 drop_table() 方法
    
    3. process_dwd_dao_version
       - 使用 ODSDetailDAO/ODSHeaderDAO 查询
       - 使用 LedgerDAO 写入结果
    
    4. merge_ods_to_db_dao_version
       - 使用 db.transaction() 管理事务
    
    5. detect_tax_anomalies_dao_version
       - 使用 DAO 查询数据
       - 使用 OADSAnalyticsDAO 保存结果
    
    6. generate_data_quality_report
       - 使用各 DAO 的 count/find 方法
       - 生成数据质量报告
    
    集成步骤：
    1. 复制相关代码到 VAT_Invoice_Processor.py
    2. 调整类名和变量名以匹配现有代码
    3. 运行单元测试验证
    4. 逐个函数测试，确保业务逻辑不变
    5. 最后移除原有的 sqlite3 直接调用
    """)
