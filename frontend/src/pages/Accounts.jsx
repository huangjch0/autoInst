import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Popconfirm, Card, Row, Col, Statistic, Tabs, Tag, Drawer, Spin, Descriptions, Progress, Empty, Select } from 'antd'
import { PlusOutlined, DeleteOutlined, EyeOutlined, SyncOutlined, LineChartOutlined, WalletOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { accountApi, assetApi } from '../api'
import dayjs from 'dayjs'

const { TextArea } = Input
const { TabPane } = Tabs
const { Option } = Select

function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [selectedAccount, setSelectedAccount] = useState(null)
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [accountSummary, setAccountSummary] = useState(null)
  const [accountTransactions, setAccountTransactions] = useState([])
  const [accountSnapshots, setAccountSnapshots] = useState([])
  const [accountPerformance, setAccountPerformance] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [assets, setAssets] = useState([])
  const [datasources, setDatasources] = useState({})

  useEffect(() => {
    fetchAccounts()
    fetchAssets()
    fetchDatasources()
  }, [])

  const fetchAccounts = async () => {
    setLoading(true)
    try {
      const data = await accountApi.getAll()
      setAccounts(data)
    } catch (error) {
      message.error('获取账户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchAssets = async () => {
    try {
      const data = await assetApi.getAll()
      setAssets(data)
    } catch (error) {
      console.error('获取资产列表失败')
    }
  }

  const fetchDatasources = async () => {
    try {
      const response = await fetch('/api/accounts/datasources')
      const data = await response.json()
      setDatasources(data)
    } catch (error) {
      console.error('获取数据源列表失败:', error)
    }
  }

  const handleAdd = () => {
    form.resetFields()
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await accountApi.delete(id)
      message.success('删除成功')
      fetchAccounts()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      await accountApi.create(values)
      message.success('添加成功')
      setModalVisible(false)
      fetchAccounts()
    } catch (error) {
      message.error('添加失败')
    }
  }

  const handleViewDetail = async (account) => {
    setSelectedAccount(account)
    setDetailDrawerVisible(true)
    setSummaryLoading(true)
    
    try {
      const [summary, transactions, snapshots, performance] = await Promise.all([
        accountApi.getSummary(account.id),
        accountApi.getTransactions(account.id),
        accountApi.getSnapshots(account.id),
        fetchAccountPerformance(account.id)
      ])
      
      setAccountSummary(summary)
      setAccountTransactions(transactions)
      setAccountSnapshots(snapshots)
      setAccountPerformance(performance)
    } catch (error) {
      message.error('获取账户详情失败')
    } finally {
      setSummaryLoading(false)
    }
  }

  const fetchAccountPerformance = async (accountId) => {
    try {
      return await fetch(`/api/accounts/${accountId}/performance?days=30`).then(r => r.json())
    } catch (error) {
      return null
    }
  }

  const handleSnapshot = async (accountId) => {
    try {
      await fetch(`/api/accounts/${accountId}/snapshot-daily`, { method: 'POST' })
      message.success('快照已创建')
      handleViewDetail(accounts.find(a => a.id === accountId))
    } catch (error) {
      message.error('创建快照失败')
    }
  }

  const columns = [
    { title: '账户名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { 
      title: '初始资金', 
      dataIndex: 'initial_capital', 
      key: 'initial_capital', 
      render: (v) => `¥${v?.toLocaleString()}` 
    },
    { 
      title: '创建时间', 
      dataIndex: 'created_at', 
      key: 'created_at', 
      render: (v) => new Date(v).toLocaleString() 
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button size="small" type="primary" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
          <Button size="small" icon={<SyncOutlined />} onClick={() => handleSnapshot(record.id)}>
            快照
          </Button>
          <Popconfirm title="确定删除该账户?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  const holdingColumns = [
    { title: '代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '持仓数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '成本价', dataIndex: 'avg_cost', key: 'avg_cost', render: (v) => `¥${v?.toFixed(2)}` },
    { 
      title: '现价', 
      dataIndex: 'current_price', 
      key: 'current_price', 
      render: (v) => v ? `¥${v.toFixed(2)}` : '-' 
    },
    { 
      title: '市值', 
      dataIndex: 'market_value', 
      key: 'market_value', 
      render: (v) => v ? `¥${v.toFixed(2)}` : '-' 
    },
    { 
      title: '盈亏', 
      dataIndex: 'profit_loss', 
      key: 'profit_loss', 
      render: (v, record) => {
        if (v === null || v === undefined) return '-'
        const color = v >= 0 ? '#3f8600' : '#cf1322'
        return <span style={{ color }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}</span>
      }
    },
    { 
      title: '盈亏%', 
      dataIndex: 'profit_loss_pct', 
      key: 'profit_loss_pct', 
      render: (v) => {
        if (v === null || v === undefined) return '-'
        const color = v >= 0 ? '#3f8600' : '#cf1322'
        return <Tag color={v >= 0 ? 'green' : 'red'}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Tag>
      }
    }
  ]

  const transactionColumns = [
    { 
      title: '日期', 
      dataIndex: 'date', 
      key: 'date',
      render: (v) => new Date(v).toLocaleDateString()
    },
    { 
      title: '类型', 
      dataIndex: 'type', 
      key: 'type', 
      render: (v) => (
        <Tag color={v === 'buy' ? 'green' : 'red'}>
          {v === 'buy' ? '买入' : '卖出'}
        </Tag>
      )
    },
    { title: '代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
    { title: '手续费', dataIndex: 'fee', key: 'fee', render: (v) => `¥${v?.toFixed(2)}` }
  ]

  const renderPortfolioChart = () => {
    if (!accountSnapshots || accountSnapshots.length === 0) {
      return <Empty description="暂无净值数据" />
    }

    const chartData = accountSnapshots.map(s => ({
      date: new Date(s.date).toLocaleDateString(),
      value: s.total_value,
      cash: s.cash,
      position: s.position_value
    }))

    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis domain={['auto', 'auto']} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke="#1890ff" name="总净值" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="cash" stroke="#52c41a" name="现金" dot={false} strokeDasharray="3 3" />
          <Line type="monotone" dataKey="position" stroke="#faad14" name="持仓市值" dot={false} strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const renderSummaryCard = () => {
    if (!accountSummary) return null

    const profitColor = accountSummary.total_profit_loss >= 0 ? '#3f8600' : '#cf1322'
    const profitIcon = accountSummary.total_profit_loss >= 0 ? <RiseOutlined /> : <FallOutlined />

    return (
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={4}>
            <Statistic 
              title="账户名称" 
              value={accountSummary.name}
              prefix={<WalletOutlined />}
            />
          </Col>
          <Col span={4}>
            <Statistic 
              title="初始资金" 
              value={accountSummary.initial_capital}
              prefix="¥"
            />
          </Col>
          <Col span={4}>
            <Statistic 
              title="当前净值" 
              value={accountSummary.current_value}
              prefix="¥"
              precision={2}
            />
          </Col>
          <Col span={4}>
            <Statistic 
              title="总盈亏" 
              value={accountSummary.total_profit_loss}
              prefix={profitIcon}
              suffix="¥"
              valueStyle={{ color: profitColor }}
            />
          </Col>
          <Col span={4}>
            <Statistic 
              title="收益率" 
              value={accountSummary.total_profit_loss_pct}
              suffix="%"
              valueStyle={{ color: profitColor }}
            />
            <Progress 
              percent={Math.min(Math.abs(accountSummary.total_profit_loss_pct), 100)} 
              showInfo={false}
              strokeColor={profitColor}
              size="small"
            />
          </Col>
          <Col span={4}>
            <Statistic 
              title="交易次数" 
              value={accountSummary.transaction_count}
            />
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Statistic 
              title="现金" 
              value={accountSummary.cash}
              prefix="¥"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="持仓市值" 
              value={accountSummary.position_value}
              prefix="¥"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="持仓数量" 
              value={accountSummary.holdings?.length || 0}
              suffix="只"
            />
          </Col>
        </Row>
      </Card>
    )
  }

  const renderPerformanceCard = () => {
    if (!accountPerformance) return null

    return (
      <Card title="账户表现 (近30天)" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic 
              title="总收益" 
              value={accountPerformance.total_return}
              suffix="%"
              valueStyle={{ color: accountPerformance.total_return >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="年化收益" 
              value={accountPerformance.annualized_return}
              suffix="%"
              valueStyle={{ color: accountPerformance.annualized_return >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="最大回撤" 
              value={accountPerformance.max_drawdown}
              suffix="%"
              valueStyle={{ color: '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="夏普比率" 
              value={accountPerformance.sharpe_ratio}
              precision={2}
            />
          </Col>
        </Row>
      </Card>
    )
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加账户
        </Button>
      </Space>

      <Row gutter={16}>
        {accounts.map(account => (
          <Col span={8} key={account.id} style={{ marginBottom: 16 }}>
            <Card 
              hoverable
              onClick={() => handleViewDetail(account)}
              actions={[
                <SyncOutlined key="snapshot" onClick={(e) => { e.stopPropagation(); handleSnapshot(account.id) }} />,
                <DeleteOutlined key="delete" onClick={(e) => { e.stopPropagation(); handleDelete(account.id) }} />
              ]}
            >
              <Card.Meta
                avatar={<WalletOutlined style={{ fontSize: 32, color: '#1890ff' }} />}
                title={account.name}
                description={account.description || '暂无描述'}
              />
              <div style={{ marginTop: 16 }}>
                <Statistic 
                  title="初始资金" 
                  value={account.initial_capital}
                  prefix="¥"
                />
              </div>
              <div style={{ marginTop: 8 }}>
                <span style={{ color: '#666', fontSize: 12 }}>数据源: </span>
                <Tag color="blue">{datasources[account.datasource] || account.datasource}</Tag>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {accounts.length === 0 && !loading && (
        <Card>
          <Empty description="暂无账户，请添加" />
        </Card>
      )}

      <Modal
        title="添加账户"
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="账户名称" rules={[{ required: true }]}>
            <Input placeholder="如: 主账户、融资账户" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="账户说明" />
          </Form.Item>
          <Form.Item name="initial_capital" label="初始资金" initialValue={0}>
            <InputNumber min={0} step={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item 
            name="datasource" 
            label="数据源" 
            initialValue="tencent"
            rules={[{ required: true, message: '请选择数据源' }]}
            extra="选择获取股票数据的数据源"
          >
            <Select placeholder="请选择数据源">
              {Object.entries(datasources).map(([key, name]) => (
                <Option key={key} value={key}>{name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={`账户详情 - ${selectedAccount?.name || ''}`}
        placement="right"
        width={900}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {summaryLoading ? (
          <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 50 }} />
        ) : (
          <>
            {renderSummaryCard()}
            {renderPerformanceCard()}
            
            <Tabs defaultActiveKey="holdings">
              <TabPane tab="持仓明细" key="holdings">
                <Table
                  columns={holdingColumns}
                  dataSource={accountSummary?.holdings || []}
                  rowKey="symbol"
                  pagination={false}
                  size="small"
                  locale={{ emptyText: '暂无持仓' }}
                />
              </TabPane>
              <TabPane tab="交易记录" key="transactions">
                <Table
                  columns={transactionColumns}
                  dataSource={accountTransactions}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                  size="small"
                  locale={{ emptyText: '暂无交易记录' }}
                />
              </TabPane>
              <TabPane tab="净值曲线" key="chart">
                {renderPortfolioChart()}
              </TabPane>
            </Tabs>
          </>
        )}
      </Drawer>
    </div>
  )
}

export default Accounts
