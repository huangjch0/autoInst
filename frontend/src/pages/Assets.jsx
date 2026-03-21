import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, Switch, TimePicker, message, Space, Popconfirm, Tag, Drawer, Spin, Card, Row, Col, Statistic, Tabs, Progress, Descriptions, Alert, Tooltip } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, SearchOutlined, SyncOutlined, LineChartOutlined, ThunderboltOutlined, SettingOutlined } from '@ant-design/icons'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend, ResponsiveContainer, ReferenceLine, ComposedChart, Bar, Area } from 'recharts'
import { assetApi, marketApi, schedulerApi } from '../api'
import dayjs from 'dayjs'

const { Option } = Select
const { TabPane } = Tabs

function Assets() {
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [searchModalVisible, setSearchModalVisible] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [editingAsset, setEditingAsset] = useState(null)
  const [form] = Form.useForm()
  const [searchForm] = Form.useForm()
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [chartData, setChartData] = useState([])
  const [chartLoading, setChartLoading] = useState(false)
  const [prediction, setPrediction] = useState(null)
  const [predictionStrategies, setPredictionStrategies] = useState([])
  const [selectedStrategy, setSelectedStrategy] = useState('ensemble')
  const [schedulerStatus, setSchedulerStatus] = useState(null)
  const [batchUpdating, setBatchUpdating] = useState(false)
  const [activeTab, setActiveTab] = useState('chart')
  const [indicatorData, setIndicatorData] = useState([])
  const [schedulerConfigVisible, setSchedulerConfigVisible] = useState(false)
  const [schedulerConfig, setSchedulerConfig] = useState({
    enabled: true,
    dailyTime: '15:30',
    intervalMinutes: 0,
    datasource: 'tencent'
  })
  const [datasources, setDatasources] = useState({})
  const [configForm] = Form.useForm()

  useEffect(() => {
    fetchAssets()
    fetchPredictionStrategies()
    fetchSchedulerStatus()
    fetchDatasources()
  }, [])

  const fetchAssets = async () => {
    setLoading(true)
    try {
      const data = await assetApi.getAll()
      setAssets(data)
    } catch (error) {
      message.error('获取资产列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchPredictionStrategies = async () => {
    try {
      const data = await marketApi.getPredictionStrategies()
      setPredictionStrategies(data)
    } catch (error) {
      console.error('获取预测策略列表失败', error)
    }
  }

  const fetchSchedulerStatus = async () => {
    try {
      const data = await schedulerApi.getStatus()
      setSchedulerStatus(data)
    } catch (error) {
      console.error('获取调度器状态失败', error)
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

  const handleOpenSchedulerConfig = async () => {
    await fetchSchedulerStatus()
    configForm.setFieldsValue({
      enabled: schedulerStatus?.running || true,
      dailyTime: dayjs('15:30', 'HH:mm'),
      intervalMinutes: 0,
      datasource: schedulerStatus?.datasource || 'tencent'
    })
    setSchedulerConfigVisible(true)
  }

  const handleSaveSchedulerConfig = async () => {
    try {
      const values = await configForm.validateFields()
      const dailyTimeStr = values.dailyTime ? values.dailyTime.format('HH:mm') : '15:30'
      
      if (values.enabled) {
        await schedulerApi.config(dailyTimeStr, values.intervalMinutes, values.datasource)
        await schedulerApi.start()
        message.success('自动更新配置已保存并启用')
      } else {
        await schedulerApi.stop()
        message.success('自动更新已停止')
      }
      
      setSchedulerConfigVisible(false)
      fetchSchedulerStatus()
    } catch (error) {
      message.error('配置保存失败')
    }
  }

  const handleAdd = () => {
    setEditingAsset(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingAsset(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await assetApi.delete(id)
      message.success('删除成功')
      fetchAssets()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingAsset) {
        await assetApi.update(editingAsset.id, values)
        message.success('更新成功')
      } else {
        await assetApi.create(values)
        message.success('添加成功')
      }
      setModalVisible(false)
      fetchAssets()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleSearch = async () => {
    const values = await searchForm.validateFields()
    setSearchLoading(true)
    try {
      const results = await marketApi.search(values.keyword)
      setSearchResults(results)
    } catch (error) {
      message.error('搜索失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSelectStock = async (stock) => {
    try {
      await assetApi.create({
        symbol: stock.symbol,
        name: stock.name,
        type: 'stock'
      })
      message.success(`${stock.name} 添加成功`)
      fetchAssets()
    } catch (error) {
      message.error('添加失败，可能已存在')
    }
  }

  const handleFetchData = async (symbol) => {
    try {
      message.loading({ content: '正在获取数据...', key: 'fetch' })
      await marketApi.fetchData(symbol)
      message.success({ content: '数据获取成功', key: 'fetch' })
    } catch (error) {
      message.error({ content: '数据获取失败', key: 'fetch' })
    }
  }

  const handleUpdateAll = async () => {
    setBatchUpdating(true)
    try {
      message.loading({ content: '正在批量更新所有资产数据...', key: 'updateAll' })
      const result = await marketApi.fetchAll()
      message.success({ 
        content: `更新完成: 成功 ${result.success} 个, 失败 ${result.failed} 个`, 
        key: 'updateAll',
        duration: 5
      })
      fetchAssets()
    } catch (error) {
      message.error({ content: '批量更新失败', key: 'updateAll' })
    } finally {
      setBatchUpdating(false)
    }
  }

  const handleViewDetail = async (record) => {
    setSelectedAsset(record)
    setDetailDrawerVisible(true)
    setChartLoading(true)
    setPrediction(null)
    setActiveTab('chart')
    try {
      const historyData = await marketApi.getHistoryWithIndicators(record.symbol)
      const formattedData = historyData.map(d => ({
        date: d.date ? new Date(d.date).toLocaleDateString() : '',
        close: d.close,
        open: d.open,
        high: d.high,
        low: d.low,
        volume: d.volume,
        ma_5: d.ma_5,
        ma_10: d.ma_10,
        ma_20: d.ma_20,
        ma_60: d.ma_60,
        rsi: d.rsi,
        macd: d.macd,
        macd_signal: d.macd_signal,
        macd_hist: d.macd_hist,
        bb_upper: d.bb_upper,
        bb_lower: d.bb_lower
      }))
      setChartData(formattedData)
      setIndicatorData(formattedData)
      
      await fetchPrediction(record.symbol, selectedStrategy)
    } catch (error) {
      message.error('获取历史数据失败')
    } finally {
      setChartLoading(false)
    }
  }

  const fetchPrediction = async (symbol, strategy) => {
    try {
      const predResult = await marketApi.predict(symbol, strategy)
      setPrediction(predResult)
    } catch (error) {
      setPrediction(null)
      if (error.response?.data?.detail) {
        message.warning(error.response.data.detail)
      }
    }
  }

  const handleStrategyChange = async (strategy) => {
    setSelectedStrategy(strategy)
    if (selectedAsset) {
      await fetchPrediction(selectedAsset.symbol, strategy)
    }
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ 
          backgroundColor: 'rgba(255, 255, 255, 0.95)', 
          padding: '12px', 
          border: '1px solid #d9d9d9',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
        }}>
          <p style={{ margin: 0, fontWeight: 'bold', marginBottom: 8 }}>{`日期: ${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ margin: 0, color: entry.color }}>
              {`${entry.name}: ${entry.value?.toFixed ? entry.value.toFixed(2) : entry.value}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  const columns = [
    { title: '代码', dataIndex: 'symbol', key: 'symbol', width: 100 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '类型', dataIndex: 'type', key: 'type', width: 100, render: (type) => {
      const typeMap = { stock: '股票', fund: '基金', crypto: '加密货币', other: '其他' }
      return <Tag>{typeMap[type] || type}</Tag>
    }},
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (v) => new Date(v).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_, record) => (
        <Space>
          <Button size="small" type="primary" icon={<LineChartOutlined />} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
          <Button size="small" icon={<SyncOutlined />} onClick={() => handleFetchData(record.symbol)}>
            更新
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  const renderPriceChart = () => (
    <ResponsiveContainer width="100%" height={350}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis yAxisId="price" domain={['auto', 'auto']} />
        <YAxis yAxisId="volume" orientation="right" hide />
        <ChartTooltip content={<CustomTooltip />} />
        <Legend />
        <Bar yAxisId="volume" dataKey="volume" fill="#8884d8" opacity={0.3} name="成交量" />
        <Line yAxisId="price" type="monotone" dataKey="close" stroke="#1890ff" name="收盘价" dot={false} strokeWidth={2} />
        <Line yAxisId="price" type="monotone" dataKey="ma_5" stroke="#52c41a" name="MA5" dot={false} strokeDasharray="3 3" />
        <Line yAxisId="price" type="monotone" dataKey="ma_10" stroke="#faad14" name="MA10" dot={false} strokeDasharray="3 3" />
        <Line yAxisId="price" type="monotone" dataKey="ma_20" stroke="#eb2f96" name="MA20" dot={false} strokeDasharray="3 3" />
      </ComposedChart>
    </ResponsiveContainer>
  )

  const renderMACDChart = () => (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis />
        <ChartTooltip content={<CustomTooltip />} />
        <Legend />
        <ReferenceLine y={0} stroke="#666" />
        <Bar dataKey="macd_hist" fill={(entry) => entry.macd_hist >= 0 ? '#52c41a' : '#ff4d4f'} name="MACD柱" />
        <Line type="monotone" dataKey="macd" stroke="#1890ff" name="MACD" dot={false} />
        <Line type="monotone" dataKey="macd_signal" stroke="#faad14" name="Signal" dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )

  const renderRSIChart = () => (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis domain={[0, 100]} />
        <ChartTooltip content={<CustomTooltip />} />
        <Legend />
        <ReferenceLine y={30} stroke="#52c41a" strokeDasharray="3 3" />
        <ReferenceLine y={70} stroke="#ff4d4f" strokeDasharray="3 3" />
        <Line type="monotone" dataKey="rsi" stroke="#722ed1" name="RSI" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )

  const renderBollingerChart = () => (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis domain={['auto', 'auto']} />
        <ChartTooltip content={<CustomTooltip />} />
        <Legend />
        <Line type="monotone" dataKey="bb_upper" stroke="#faad14" name="布林上轨" dot={false} strokeDasharray="3 3" />
        <Line type="monotone" dataKey="close" stroke="#1890ff" name="收盘价" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="bb_lower" stroke="#52c41a" name="布林下轨" dot={false} strokeDasharray="3 3" />
      </LineChart>
    </ResponsiveContainer>
  )

  const renderPredictionCard = () => {
    if (!prediction) return null

    const directionConfig = {
      up: { text: '看涨', color: '#3f8600', icon: '↑' },
      down: { text: '看跌', color: '#cf1322', icon: '↓' },
      hold: { text: '震荡', color: '#faad14', icon: '→' }
    }
    
    const config = directionConfig[prediction.direction] || directionConfig.hold

    return (
      <Card 
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#1890ff' }} />
            <span>预测分析</span>
            <Select 
              value={selectedStrategy} 
              onChange={handleStrategyChange}
              style={{ width: 200, marginLeft: 16 }}
              size="small"
            >
              {predictionStrategies.map(s => (
                <Option key={s.name} value={s.name}>{s.description}</Option>
              ))}
            </Select>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, color: config.color }}>{config.icon}</div>
              <Statistic 
                title="预测方向" 
                value={config.text}
                valueStyle={{ color: config.color, fontSize: 24 }}
              />
            </div>
          </Col>
          <Col span={6}>
            <Statistic 
              title="置信度" 
              value={prediction.confidence ? (prediction.confidence * 100).toFixed(1) : 0}
              suffix="%"
              valueStyle={{ 
                color: prediction.confidence > 0.7 ? '#3f8600' : prediction.confidence > 0.5 ? '#faad14' : '#cf1322'
              }}
            />
            <Progress 
              percent={prediction.confidence * 100} 
              showInfo={false}
              strokeColor={prediction.confidence > 0.7 ? '#3f8600' : prediction.confidence > 0.5 ? '#faad14' : '#cf1322'}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="预测价格" 
              value={prediction.predicted_price?.toFixed(2) || '-'}
              prefix="¥"
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="使用策略" 
              value={prediction.strategy || '-'}
            />
          </Col>
        </Row>
        
        {prediction.vote_summary && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={24}>
              <div style={{ marginBottom: 8 }}>
                <strong>投票结果:</strong>
                <Space style={{ marginLeft: 16 }}>
                  <Tag color="green">看涨 {prediction.vote_summary.up} 票</Tag>
                  <Tag color="red">看跌 {prediction.vote_summary.down} 票</Tag>
                  <Tag color="gold">震荡 {prediction.vote_summary.hold} 票</Tag>
                </Space>
              </div>
            </Col>
          </Row>
        )}

        {prediction.individual_predictions && prediction.individual_predictions.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <strong>各策略预测:</strong>
            <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
              {prediction.individual_predictions.map((p, idx) => (
                <Col span={8} key={idx}>
                  <Card size="small">
                    <Space direction="vertical" size={0}>
                      <span style={{ fontWeight: 'bold' }}>{p.strategy}</span>
                      <Tag color={p.direction === 'up' ? 'green' : p.direction === 'down' ? 'red' : 'gold'}>
                        {p.direction === 'up' ? '看涨' : p.direction === 'down' ? '看跌' : '震荡'}
                      </Tag>
                      <span style={{ fontSize: 12, color: '#666' }}>
                        置信度: {(p.confidence * 100).toFixed(1)}%
                      </span>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <strong>预测依据:</strong>
          <Alert 
            message={prediction.reason || '无'} 
            type="info" 
            style={{ marginTop: 8 }}
          />
        </div>

        {prediction.indicators && (
          <Descriptions size="small" column={4} style={{ marginTop: 16 }}>
            {Object.entries(prediction.indicators).map(([key, value]) => (
              value !== null && value !== undefined && (
                <Descriptions.Item key={key} label={key}>{value}</Descriptions.Item>
              )
            ))}
          </Descriptions>
        )}
      </Card>
    )
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          手动添加
        </Button>
        <Button icon={<SearchOutlined />} onClick={() => setSearchModalVisible(true)}>
          搜索添加
        </Button>
        <Button 
          type="primary" 
          icon={<SyncOutlined spin={batchUpdating} />} 
          onClick={handleUpdateAll}
          loading={batchUpdating}
        >
          一键更新所有数据
        </Button>
        <Button 
          icon={<SettingOutlined />} 
          onClick={handleOpenSchedulerConfig}
        >
          自动更新: {schedulerStatus?.running ? `已启用 (${datasources[schedulerStatus?.datasource] || schedulerStatus?.datasource || '腾讯API'})` : '已停止'}
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={assets}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1000 }}
      />

      <Modal
        title={editingAsset ? '编辑资产' : '添加资产'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="symbol" label="代码" rules={[{ required: true }]}>
            <Input disabled={!!editingAsset} placeholder="如: 000001" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如: 平安银行" />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select>
              <Option value="stock">股票</Option>
              <Option value="fund">基金</Option>
              <Option value="crypto">加密货币</Option>
              <Option value="other">其他</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="搜索股票"
        open={searchModalVisible}
        onCancel={() => setSearchModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={searchForm} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="keyword" rules={[{ required: true }]}>
            <Input placeholder="输入股票代码或名称" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSearch} loading={searchLoading}>
              搜索
            </Button>
          </Form.Item>
        </Form>
        <Table
          columns={[
            { title: '代码', dataIndex: 'symbol' },
            { title: '名称', dataIndex: 'name' },
            { title: '现价', dataIndex: 'price', render: (v) => v ? `¥${v}` : '-' },
            { title: '涨跌幅', dataIndex: 'change_percent', render: (v) => (
              <span style={{ color: v >= 0 ? '#3f8600' : '#cf1322' }}>{v}%</span>
            )},
            { title: '操作', render: (_, record) => (
              <Button size="small" type="primary" onClick={() => handleSelectStock(record)}>
                添加
              </Button>
            )}
          ]}
          dataSource={searchResults}
          rowKey="symbol"
          size="small"
          pagination={false}
        />
      </Modal>

      <Modal
        title="自动更新配置"
        open={schedulerConfigVisible}
        onOk={handleSaveSchedulerConfig}
        onCancel={() => setSchedulerConfigVisible(false)}
        okText="保存配置"
      >
        <Form form={configForm} layout="vertical">
          <Form.Item name="enabled" label="启用自动更新" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
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
          <Form.Item 
            name="dailyTime" 
            label="每日更新时间"
            extra="每日固定时间自动更新所有资产数据"
          >
            <TimePicker format="HH:mm" style={{ width: '100%' }} placeholder="选择更新时间" />
          </Form.Item>
          <Form.Item 
            name="intervalMinutes" 
            label="间隔更新（分钟）" 
            initialValue={0}
            extra="设置为0则只使用每日定时更新，大于0则每隔指定分钟更新一次"
          >
            <InputNumber min={0} max={1440} style={{ width: '100%' }} placeholder="0表示不启用间隔更新" />
          </Form.Item>
        </Form>
        {schedulerStatus?.jobs?.length > 0 && (
          <Alert
            type="info"
            style={{ marginTop: 16 }}
            message={
              <div>
                <div><strong>当前任务:</strong></div>
                {schedulerStatus.jobs.map((job, idx) => (
                  <div key={idx}>{job.job} - 下次执行: {job.next_run || '未知'}</div>
                ))}
              </div>
            }
          />
        )}
      </Modal>

      <Drawer
        title={`${selectedAsset?.name || ''} (${selectedAsset?.symbol || ''})`}
        placement="right"
        width={900}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {chartLoading ? (
          <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 50 }} />
        ) : (
          <>
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              <TabPane tab="K线图" key="chart">
                <Card title="价格走势与均线" size="small">
                  {renderPriceChart()}
                </Card>
              </TabPane>
              <TabPane tab="MACD" key="macd">
                <Card title="MACD指标" size="small">
                  {renderMACDChart()}
                </Card>
              </TabPane>
              <TabPane tab="RSI" key="rsi">
                <Card title="RSI指标" size="small">
                  {renderRSIChart()}
                </Card>
              </TabPane>
              <TabPane tab="布林带" key="bollinger">
                <Card title="布林带" size="small">
                  {renderBollingerChart()}
                </Card>
              </TabPane>
            </Tabs>
            
            {renderPredictionCard()}
          </>
        )}
      </Drawer>
    </div>
  )
}

export default Assets
