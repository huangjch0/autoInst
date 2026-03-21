import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Table, Tag, Spin, message, Empty } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { accountApi, strategyApi } from '../api'
import { useAccount } from '../App'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']

function Dashboard() {
  const { currentAccount } = useAccount()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [snapshots, setSnapshots] = useState([])
  const [signals, setSignals] = useState([])

  useEffect(() => {
    if (currentAccount) {
      fetchData()
    }
  }, [currentAccount])

  const fetchData = async () => {
    if (!currentAccount) return
    
    setLoading(true)
    try {
      const [summaryRes, snapshotsRes, signalsRes] = await Promise.all([
        accountApi.getSummary(currentAccount.id),
        accountApi.getSnapshots(currentAccount.id),
        strategyApi.getSignals({ status: 'pending' })
      ])
      setSummary(summaryRes)
      setSnapshots(snapshotsRes)
      setSignals(signalsRes)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const pieData = summary?.holdings?.map(h => ({
    name: h.name || h.symbol,
    value: h.market_value || 0
  })) || []

  const chartData = snapshots.map(s => ({
    date: new Date(s.date).toLocaleDateString(),
    value: s.total_value
  }))

  const holdingColumns = [
    { title: '代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '持仓数量', dataIndex: 'quantity', key: 'quantity', render: (v) => v?.toFixed(2) },
    { title: '成本价', dataIndex: 'avg_cost', key: 'avg_cost', render: (v) => `¥${v?.toFixed(2)}` },
    { title: '现价', dataIndex: 'current_price', key: 'current_price', render: (v) => v ? `¥${v?.toFixed(2)}` : '-' },
    { title: '市值', dataIndex: 'market_value', key: 'market_value', render: (v) => v ? `¥${v?.toFixed(2)}` : '-' },
    { title: '盈亏', dataIndex: 'profit_loss', key: 'profit_loss', render: (v, record) => (
      <span style={{ color: (v || 0) >= 0 ? '#3f8600' : '#cf1322' }}>
        {v >= 0 ? '+' : ''}{v?.toFixed(2)} ({record.profit_loss_pct?.toFixed(2)}%)
      </span>
    )}
  ]

  const signalColumns = [
    { title: '资产', dataIndex: 'symbol', key: 'symbol' },
    { title: '名称', dataIndex: 'asset_name', key: 'asset_name' },
    { title: '信号类型', dataIndex: 'signal_type', key: 'signal_type', render: (type) => {
      const colorMap = { buy: 'green', sell: 'red', hold: 'orange' }
      const textMap = { buy: '买入', sell: '卖出', hold: '观望' }
      return <Tag color={colorMap[type]}>{textMap[type]}</Tag>
    }},
    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => v ? `¥${v?.toFixed(2)}` : '-' },
    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true }
  ]

  if (!currentAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Empty description="请先选择账户" />
      </div>
    )
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="账户总值"
              value={summary?.current_value || 0}
              precision={2}
              prefix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="初始资金"
              value={summary?.initial_capital || currentAccount?.initial_capital || 0}
              precision={2}
              prefix="¥"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总盈亏"
              value={summary?.total_profit_loss || 0}
              precision={2}
              valueStyle={{ color: (summary?.total_profit_loss || 0) >= 0 ? '#3f8600' : '#cf1322' }}
              prefix={(summary?.total_profit_loss || 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="收益率"
              value={summary?.total_profit_loss_pct || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: (summary?.total_profit_loss_pct || 0) >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="持仓分布">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 50 }}>暂无持仓数据</div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="净值曲线">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#1890ff" name="账户净值" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 50 }}>暂无净值数据</div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="持仓明细">
            <Table
              columns={holdingColumns}
              dataSource={summary?.holdings || []}
              rowKey="symbol"
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无持仓' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="待处理信号">
            <Table
              columns={signalColumns}
              dataSource={signals}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无待处理信号' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
