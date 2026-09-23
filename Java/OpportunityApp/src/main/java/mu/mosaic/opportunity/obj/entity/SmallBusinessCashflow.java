package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.math.BigDecimal;

/**
 * One row of small_business_cashflow.csv, columns named as in the file: one business's one month from the synthetic
 * hackathon practice dataset. A separate profile, never joined to the Olist tables; record_id is a row id, not a business.
 * Describes the file only: it is not in BusinessDatabase.TABLES, so nothing imports or exports it, and the Python API
 * reads AI/datasets/small_business_cashflow.csv directly.
 */
@Entity
@Table(name = "small_business_cashflow")
public class SmallBusinessCashflow extends DatabaseObject.ID_RECORD_OBJ<Long, SmallBusinessCashflow> {
    @Column(name = "record_id")
    private String recordId;
    @Column(name = "sector")
    private String sector;
    @Column(name = "employees")
    private Integer employees;
    @Column(name = "month")
    private String month;
    @Column(name = "revenue_usd")
    private BigDecimal revenueUsd;
    @Column(name = "opex_usd")
    private BigDecimal opexUsd;
    @Column(name = "accounts_receivable_days")
    private Integer accountsReceivableDays;
    @Column(name = "inventory_days")
    private Integer inventoryDays;
    @Column(name = "loan_balance_usd")
    private BigDecimal loanBalanceUsd;
    @Column(name = "owner_injections_usd")
    private BigDecimal ownerInjectionsUsd;
    @Column(name = "cashflow_stress_next_month")
    private Integer cashflowStressNextMonth;

    protected SmallBusinessCashflow() {}
}
