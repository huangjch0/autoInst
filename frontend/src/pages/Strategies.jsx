import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, InputNumber, Switch, message, Space, Popconfirm, Tag, Card, Empty, Row, Col, Tooltip, Descriptions, Statistic, Alert } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, PlayCircleOutlined, ClockCircleOutlined, SyncOutlined, RiseOutlined, FallOutlined, DollarOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { strategyApi } from '../api'
import { useAccount, usePendingCount } from '../App'

const { Option } = Select
const { TextArea } = Input

const strategyTemplates = {
  ma_cross: {
    name: '均线交叉策略',
    params: { short_period: 5, long_period: 20 }
  },
  rsi: {
    name: 'RSI策略',
    params: { period: 14, oversold: 30, overbought: 70 }
  },
  macd: {
    name: 'MACD策略',
    params: { fast: 12, slow: 26, signal: 9 }
  },
  bollinger: {
    name: '布林带策略',
    params: { period: 20, std_dev: 2 }
  },
  kdj: {
    name: 'KDJ策略',
    params: { n: 9, m1: 3, m2: 3 }
  }
}

function Strategies() {
  const { currentAccount } = useAccount()
  const { refreshPendingCount } = usePendingCount()
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingStrategy, setEditingStrategy] = useState(null)
  const [selectedStrategyType, setSelectedStrategyType] = useState('ma_cross')
  const [reportModalVisible, setReportModalVisible] = useState(false)
  const [executionReport, setExecutionReport] = useState(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    if (!currentAccount) return
    
    setLoading(true)
    try {
      const strategiesData = await strategyApi.getAll({ account_id: currentAccount.id })
      setStrategies(strategiesData)
    } catch (error) {
      console.error('获取数据失败:', error)
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (currentAccount) {
      fetchData()
    }
  }, [currentAccount])

  const handleAdd = () => {
    if (!currentAccount) {
      message.warning('请先选择账户')
      return
    }
    setEditingStrategy(null)
    setSelectedStrategyType('ma_cross')
    form.resetFields()
    form.setFieldsValue({
      name: '',
      description: '',
      strategy_type: 'ma_cross',
      params: strategyTemplates.ma_cross.params,
      auto_run: true,
      run_interval_minutes: 60
    })
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingStrategy(record)
    let params = {}
    try {
      params = record.params_json ? JSON.parse(record.params_json) : {}
    } catch (e) {
      console.error('解析参数失败:', e)
    }
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      is_active: record.is_active === 1,
      auto_run: record.auto_run === 1,
      run_interval_minutes: record.run_interval_minutes || 60,
      params
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await strategyApi.delete(id)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const data = {
        account_id: currentAccount.id,
        name: values.name,
        description: values.description,
        params: {
          name: values.strategy_type,
          ...values.params
        },
        auto_run: values.auto_run ? 1 : 0,
        run_interval_minutes: values.run_interval_minutes || 60
      }
      if (editingStrategy) {
        await strategyApi.update(editingStrategy.id, data)
        message.success('更新成功')
      } else {
        await strategyApi.create(data)
        message.success('添加成功')
      }
      setModalVisible(false)
      fetchData()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleRunStrategy = async (id) => {
    try {
      message.loading({ content: '正在执行策略...', key: 'run' })
      const result = await strategyApi.run(id)
      message.success({ content: `策略执行完成，生成 ${result.signals?.length || 0} 个信号`, key: 'run' })
      
      const buySignals = result.signals?.filter(s => s.signal_type === 'buy') || []
      const sellSignals = result.signals?.filter(s => s.signal_type === 'sell') || []
      const holdSignals = result.signals?.filter(s => s.signal_type === 'hold') || []
      
      const totalBuyAmount = buySignals.reduce((sum, s) => sum + (s.suggested_quantity || 100) * (s.price || 0), 0)
      const pendingSignals = result.signals?.filter(s => s.id) || []
      
      setExecutionReport({
        strategyName: strategies.find(s => s.id === id)?.name || '策略',
        totalSignals: result.signals?.length || 0,
        buyCount: buySignals.length,
        sellCount: sellSignals.length,
        holdCount: holdSignals.length,
        totalBuyAmount,
        pendingCount: pendingSignals.length,
        signals: result.signals || [],
        executionTime: new Date().toLocaleString()
      })
      setReportModalVisible(true)
      
      fetchData()
      refreshPendingCount()
    } catch (error) {
      message.error({ content: '执行失败', key: 'run' })
    }
  }

  const handleToggleAutoRun = async (id, checked) => {
    try {
      await strategyApi.update(id, { auto_run: checked ? 1 : 0 })
      message.success(checked ? '已开启自动执行' : '已关闭自动执行')
      fetchData()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const strategyColumns = [
    { 
      title: '策略名称', 
      dataIndex: 'name', 
      key: 'name',
      width: 150,
      render: (name, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {record.description && (
            <div style={{ fontSize: 12, color: '#999' }}>{record.description}</div>
          )}
        </div>
      )
    },
    { 
      title: '状态', 
      key: 'status', 
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={record.is_active === 1 ? 'green' : 'default'}>
            {record.is_active === 1 ? '启用' : '禁用'}
          </Tag>
          {record.auto_run === 1 && (
            <Tag color="blue" icon={<SyncOutlined spin />}>自动</Tag>
          )}
        </Space>
      )
    },
    { 
      title: '自动执行', 
      dataIndex: 'auto_run', 
      key: 'auto_run', 
      width: 100,
      render: (v, record) => (
        <Switch 
          checked={v === 1} 
          onChange={(checked) => handleToggleAutoRun(record.id, checked)}
          checkedChildren="开"
          unCheckedChildren="关"
          size="small"
        />
      )
    },
    { 
      title: '执行信息', 
      key: 'run_info', 
      width: 180,
      render: (_, record) => (
        <div style={{ fontSize: 12 }}>
          <div>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            间隔: {record.run_interval_minutes || 60}分钟
          </div>
          <div style={{ color: '#999' }}>
            上次: {record.last_run_at ? new Date(record.last_run_at).toLocaleString() : '未执行'}
          </div>
        </div>
      )
    },
    { 
      title: '创建时间', 
      dataIndex: 'created_at', 
      key: 'created_at', 
      width: 150,
      render: (v) => <span style={{ fontSize: 12, color: '#999' }}>{new Date(v).toLocaleString()}</span>
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="立即执行">
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleRunStrategy(record.id)}>
              执行
            </Button>
          </Tooltip>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  const renderParamFields = () => {
    const template = strategyTemplates[selectedStrategyType]
    if (!template) return null
    
    return Object.entries(template.params).map(([key, defaultValue]) => (
      <Col span={12} key={key}>
        <Form.Item name={['params', key]} label={key} initialValue={defaultValue}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      </Col>
    ))
  }

  if (!currentAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Empty description="请先选择账户" />
      </div>
    )
  }

  return (
    <div>
      <Card title={`策略列表 - ${currentAccount.name}`}>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加策略
          </Button>
        </Space>
        <Table
          columns={strategyColumns}
          dataSource={strategies}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title={editingStrategy ? '编辑策略' : '添加策略'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="策略名称" rules={[{ required: true }]}>
                <Input placeholder="输入策略名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="strategy_type" label="策略类型" rules={[{ required: true }]}>
                <Select onChange={(v) => {
                  setSelectedStrategyType(v)
                  form.setFieldsValue({ params: strategyTemplates[v].params })
                }}>
                  {Object.entries(strategyTemplates).map(([key, value]) => (
                    <Option key={key} value={key}>{value.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="策略描述（可选）" />
          </Form.Item>
          <Form.Item label="策略参数">
            <Row gutter={16}>
              {renderParamFields()}
            </Row>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="auto_run" label="自动执行" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="run_interval_minutes" label="执行间隔(分钟)">
                <InputNumber min={5} max={1440} style={{ width: '100%' }} placeholder="60" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title="策略执行报告"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        footer={null}
        width={800}
      >
        {executionReport && (
          <div>
            <Alert
              message={`策略 [${executionReport.strategyName}] 执行完成`}
              description={`执行时间: ${executionReport.executionTime}`}
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic 
                  title="总信号数" 
                  value={executionReport.totalSignals}
                  suffix="个"
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="买入信号" 
                  value={executionReport.buyCount}
                  suffix="个"
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<RiseOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="卖出信号" 
                  value={executionReport.sellCount}
                  suffix="个"
                  valueStyle={{ color: '#f5222d' }}
                  prefix={<FallOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="待审批" 
                  value={executionReport.pendingCount}
                  suffix="个"
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            </Row>

            {executionReport.buyCount > 0 && (
              <Card title="买入信号详情" size="small" style={{ marginBottom: 16 }}>
                <Table
                  dataSource={executionReport.signals.filter(s => s.signal_type === 'buy')}
                  rowKey="symbol"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '股票', dataIndex: 'symbol', key: 'symbol', render: (v, r) => `${v} ${r.name}` },
                    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
                    { title: '建议股数', dataIndex: 'suggested_quantity', key: 'suggested_quantity', render: (v) => <span style={{ color: '#1890ff', fontWeight: 500 }}>{v || 100}股</span> },
                    { title: '预估金额', key: 'amount', render: (_, r) => <span style={{ color: '#f50' }}>¥{((r.suggested_quantity || 100) * (r.price || 0)).toFixed(2)}</span> },
                    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true }
                  ]}
                />
              </Card>
            )}

            {executionReport.sellCount > 0 && (
              <Card title="卖出信号详情" size="small" style={{ marginBottom: 16 }}>
                <Table
                  dataSource={executionReport.signals.filter(s => s.signal_type === 'sell')}
                  rowKey="symbol"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '股票', dataIndex: 'symbol', key: 'symbol', render: (v, r) => `${v} ${r.name}` },
                    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
                    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true }
                  ]}
                />
              </Card>
            )}

            {executionReport.holdCount > 0 && (
              <Card title="观望信号" size="small">
                <Table
                  dataSource={executionReport.signals.filter(s => s.signal_type === 'hold')}
                  rowKey="symbol"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '股票', dataIndex: 'symbol', key: 'symbol', render: (v, r) => `${v} ${r.name}` },
                    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
                    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true }
                  ]}
                />
              </Card>
            )}

            {executionReport.pendingCount > 0 && (
              <Alert
                message={`有 ${executionReport.pendingCount} 个信号待审批，请前往审批中心处理`}
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Strategies
