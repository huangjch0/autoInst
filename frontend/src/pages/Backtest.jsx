import React, { useState, useEffect } from 'react'
import { Card, Form, Select, DatePicker, InputNumber, Button, message, Row, Col, Statistic, Table, Spin, Tabs, Tag, Space, Alert, Empty } from 'antd'
import { PlayCircleOutlined, RiseOutlined, FallOutlined, TrophyOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, ScatterChart, Scatter, ComposedChart, ZAxis } from 'recharts'
import { backtestApi, assetApi } from '../api'
import { useAccount } from '../App'

const { Option } = Select
const { RangePicker } = DatePicker
const { TabPane } = Tabs

const strategyOptions = [
  { value: 'ma_cross', label: '均线交叉策略' },
  { value: 'rsi', label: 'RSI策略' },
  { value: 'macd', label: 'MACD策略' },
  { value: 'bollinger', label: '布林带策略' },
  { value: 'kdj', label: 'KDJ策略' },
  { value: 'time_series', label: '时序预测策略' }
]

function Backtest() {
  const { currentAccount } = useAccount()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [form] = Form.useForm()
  const [selectedStrategy, setSelectedStrategy] = useState(null)

  const fetchAssets = async () => {
    try {
      const data = await assetApi.getAll()
      setAssets(data)
    } catch (error) {
      message.error('获取资产列表失败')
    }
  }

  useEffect(() => {
    if (currentAccount) {
      fetchAssets()
    }
  }, [currentAccount])

  if (!currentAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Empty description="请先选择账户" />
      </div>
    )
  }

  const handleRunBacktest = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      setSelectedStrategy(values.strategy_name)
      
      const strategyParams = {}
      if (values.strategy_name === 'ma_cross') {
        strategyParams.short_period = values.short_period || 5
        strategyParams.long_period = values.long_period || 20
      } else if (values.strategy_name === 'rsi') {
        strategyParams.period = values.period || 14
        strategyParams.oversold = values.oversold || 30
        strategyParams.overbought = values.overbought || 70
      } else if (values.strategy_name === 'macd') {
        strategyParams.fast = values.fast || 12
        strategyParams.slow = values.slow || 26
        strategyParams.signal = values.signal || 9
      } else if (values.strategy_name === 'bollinger') {
        strategyParams.period = values.bollinger_period || 20
        strategyParams.std_dev = values.std_dev || 2
      } else if (values.strategy_name === 'kdj') {
        strategyParams.n = values.kdj_n || 9
        strategyParams.m1 = values.kdj_m1 || 3
        strategyParams.m2 = values.kdj_m2 || 3
      } else if (values.strategy_name === 'time_series') {
        strategyParams.lookback = values.lookback || 20
        strategyParams.threshold = values.threshold || 0.02
      }

      const data = await backtestApi.run({
        symbol: values.symbol,
        strategy_name: values.strategy_name,
        strategy_params: strategyParams,
        start_date: values.date_range[0].format('YYYY-MM-DD'),
        end_date: values.date_range[1].format('YYYY-MM-DD'),
        initial_capital: values.initial_capital || 100000
      })
      
      setResult(data)
      message.success('回测完成')
    } catch (error) {
      message.error('回测失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const renderStrategyParams = () => {
    const strategyName = form.getFieldValue('strategy_name')
    
    if (strategyName === 'ma_cross') {
      return (
        <>
          <Col span={8}>
            <Form.Item name="short_period" label="短期均线" initialValue={5}>
              <InputNumber min={1} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="long_period" label="长期均线" initialValue={20}>
              <InputNumber min={1} max={200} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    } else if (strategyName === 'rsi') {
      return (
        <>
          <Col span={6}>
            <Form.Item name="period" label="RSI周期" initialValue={14}>
              <InputNumber min={1} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="oversold" label="超卖阈值" initialValue={30}>
              <InputNumber min={0} max={50} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="overbought" label="超买阈值" initialValue={70}>
              <InputNumber min={50} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    } else if (strategyName === 'macd') {
      return (
        <>
          <Col span={6}>
            <Form.Item name="fast" label="快线周期" initialValue={12}>
              <InputNumber min={1} max={50} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="slow" label="慢线周期" initialValue={26}>
              <InputNumber min={1} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="signal" label="信号线周期" initialValue={9}>
              <InputNumber min={1} max={50} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    } else if (strategyName === 'bollinger') {
      return (
        <>
          <Col span={8}>
            <Form.Item name="bollinger_period" label="周期" initialValue={20}>
              <InputNumber min={5} max={50} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="std_dev" label="标准差倍数" initialValue={2}>
              <InputNumber min={1} max={3} step={0.5} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    } else if (strategyName === 'kdj') {
      return (
        <>
          <Col span={6}>
            <Form.Item name="kdj_n" label="N值" initialValue={9}>
              <InputNumber min={1} max={30} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="kdj_m1" label="M1值" initialValue={3}>
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={6}>
            <Form.Item name="kdj_m2" label="M2值" initialValue={3}>
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    } else if (strategyName === 'time_series') {
      return (
        <>
          <Col span={8}>
            <Form.Item name="lookback" label="回看周期" initialValue={20}>
              <InputNumber min={5} max={60} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="threshold" label="趋势阈值" initialValue={0.02}>
              <InputNumber min={0.01} max={0.1} step={0.01} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </>
      )
    }
    return null
  }

  const tradeColumns = [
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
    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '金额', dataIndex: 'value', key: 'value', render: (v) => `¥${v?.toFixed(2)}` }
  ]

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
              {`${entry.name}: ¥${entry.value?.toFixed ? entry.value.toFixed(2) : entry.value}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  const renderPortfolioChart = () => {
    if (!result?.portfolio_values || result.portfolio_values.length === 0) return null

    const chartData = result.portfolio_values.map((pv, idx) => {
      const benchmark = result.benchmark_values[idx]
      const buyPoint = result.buy_points?.find(bp => bp.date === pv.date)
      const sellPoint = result.sell_points?.find(sp => sp.date === pv.date)
      
      return {
        date: new Date(pv.date).toLocaleDateString(),
        portfolioValue: pv.value,
        benchmarkValue: benchmark?.value,
        close: pv.close,
        buySignal: buyPoint ? pv.value : null,
        sellSignal: sellPoint ? pv.value : null
      }
    })

    return (
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis yAxisId="value" domain={['auto', 'auto']} />
          <YAxis yAxisId="price" orientation="right" domain={['auto', 'auto']} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line 
            yAxisId="value"
            type="monotone" 
            dataKey="portfolioValue" 
            stroke="#1890ff" 
            name="策略净值" 
            dot={false} 
            strokeWidth={2} 
          />
          <Line 
            yAxisId="value"
            type="monotone" 
            dataKey="benchmarkValue" 
            stroke="#8c8c8c" 
            name="基准净值" 
            dot={false} 
            strokeDasharray="5 5" 
          />
          <Scatter 
            yAxisId="value"
            dataKey="buySignal" 
            fill="#52c41a" 
            name="买入点"
            shape="triangle"
            fontSize={16}
          />
          <Scatter 
            yAxisId="value"
            dataKey="sellSignal" 
            fill="#ff4d4f" 
            name="卖出点"
            shape="triangle"
            fontSize={16}
          />
        </ComposedChart>
      </ResponsiveContainer>
    )
  }

  const renderPriceWithSignals = () => {
    if (!result?.portfolio_values || result.portfolio_values.length === 0) return null

    const chartData = result.portfolio_values.map((pv) => {
      const buyPoint = result.buy_points?.find(bp => bp.date === pv.date)
      const sellPoint = result.sell_points?.find(sp => sp.date === pv.date)
      
      return {
        date: new Date(pv.date).toLocaleDateString(),
        close: pv.close,
        buySignal: buyPoint ? pv.close : null,
        sellSignal: sellPoint ? pv.close : null
      }
    })

    return (
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis domain={['auto', 'auto']} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="close" 
            stroke="#1890ff" 
            name="收盘价" 
            dot={false} 
            strokeWidth={2} 
          />
          <Scatter 
            dataKey="buySignal" 
            fill="#52c41a" 
            name="买入点"
            shape="triangle"
            fontSize={16}
          />
          <Scatter 
            dataKey="sellSignal" 
            fill="#ff4d4f" 
            name="卖出点"
            shape="triangle"
            fontSize={16}
          />
        </ComposedChart>
      </ResponsiveContainer>
    )
  }

  return (
    <div>
      <Card title="回测配置">
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="symbol" label="资产代码" rules={[{ required: true }]}>
                <Select showSearch placeholder="选择资产">
                  {assets.map(a => (
                    <Option key={a.id} value={a.symbol}>{a.symbol} - {a.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="strategy_name" label="策略" rules={[{ required: true }]}>
                <Select placeholder="选择策略">
                  {strategyOptions.map(s => (
                    <Option key={s.value} value={s.value}>{s.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="initial_capital" label="初始资金" initialValue={100000}>
                <InputNumber min={10000} step={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="date_range" label="回测时间段" rules={[{ required: true }]} 
                initialValue={[dayjs().subtract(1, 'year'), dayjs()]}>
                <RangePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            {renderStrategyParams()}
          </Row>
          <Form.Item>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRunBacktest} loading={loading}>
              开始回测
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 50 }} />}

      {result && !loading && (
        <>
          <Card title="回测结果" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={4}>
                <Statistic
                  title="总收益率"
                  value={result.total_return}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: result.total_return >= 0 ? '#3f8600' : '#cf1322' }}
                  prefix={result.total_return >= 0 ? <RiseOutlined /> : <FallOutlined />}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="年化收益率"
                  value={result.annual_return}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: result.annual_return >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="最大回撤"
                  value={result.max_drawdown}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="夏普比率"
                  value={result.sharpe_ratio}
                  precision={2}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="胜率"
                  value={result.win_rate}
                  suffix="%"
                  prefix={<TrophyOutlined />}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="基准收益"
                  value={result.benchmark_return}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: result.benchmark_return >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={6}>
                <Statistic title="总交易次数" value={result.total_trades} />
              </Col>
              <Col span={6}>
                <Statistic title="盈利次数" value={result.profit_trades} valueStyle={{ color: '#3f8600' }} />
              </Col>
              <Col span={6}>
                <Statistic title="亏损次数" value={result.loss_trades} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="最终净值" 
                  value={result.final_value} 
                  prefix="¥"
                  precision={2}
                />
              </Col>
            </Row>
            
            {result.total_return > result.benchmark_return && (
              <Alert 
                message={`策略跑赢基准 ${((result.total_return - result.benchmark_return)).toFixed(2)}%`}
                type="success"
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
            {result.total_return <= result.benchmark_return && result.benchmark_return !== 0 && (
              <Alert 
                message={`策略跑输基准 ${((result.benchmark_return - result.total_return)).toFixed(2)}%`}
                type="warning"
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
          </Card>

          <Card title="净值曲线与买卖点" style={{ marginTop: 16 }}>
            <Tabs defaultActiveKey="portfolio">
              <TabPane tab="净值曲线" key="portfolio">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Tag color="blue">策略净值</Tag>
                    <Tag color="default">基准净值</Tag>
                    <Tag color="green">▲ 买入点</Tag>
                    <Tag color="red">▼ 卖出点</Tag>
                  </div>
                  {renderPortfolioChart()}
                </Space>
              </TabPane>
              <TabPane tab="价格与信号" key="price">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Tag color="blue">收盘价</Tag>
                    <Tag color="green">▲ 买入点</Tag>
                    <Tag color="red">▼ 卖出点</Tag>
                  </div>
                  {renderPriceWithSignals()}
                </Space>
              </TabPane>
            </Tabs>
          </Card>

          <Card title="交易记录" style={{ marginTop: 16 }}>
            <Table
              columns={tradeColumns}
              dataSource={result.trades}
              rowKey={(record, index) => index}
              pagination={{ pageSize: 10 }}
              size="small"
              summary={() => (
                <Table.Summary fixed>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={3}>
                      <strong>交易汇总</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={1}>
                      <strong>{result.trades?.length || 0} 笔</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2}>
                      <strong>
                        盈利: <span style={{ color: '#3f8600' }}>{result.profit_trades}</span> | 
                        亏损: <span style={{ color: '#cf1322' }}>{result.loss_trades}</span>
                      </strong>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </Card>
        </>
      )}
    </div>
  )
}

export default Backtest
