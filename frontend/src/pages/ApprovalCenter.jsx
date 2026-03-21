import React, { useState, useEffect } from 'react'
import { Table, Button, Space, Tag, Card, Empty, Modal, Descriptions, message, Tooltip, Statistic, Row, Col, InputNumber, Form, Alert } from 'antd'
import { CheckOutlined, CloseOutlined, DollarOutlined, RiseOutlined, FallOutlined, WarningOutlined } from '@ant-design/icons'
import { strategyApi, accountApi } from '../api'
import { useAccount, usePendingCount } from '../App'

function ApprovalCenter() {
  const { currentAccount } = useAccount()
  const { refreshPendingCount } = usePendingCount()
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedSignal, setSelectedSignal] = useState(null)
  const [approveModalVisible, setApproveModalVisible] = useState(false)
  const [approvingSignal, setApprovingSignal] = useState(null)
  const [approveQuantity, setApproveQuantity] = useState(100)
  const [accountSummary, setAccountSummary] = useState(null)

  const fetchData = async () => {
    if (!currentAccount) return
    
    setLoading(true)
    try {
      const data = await strategyApi.getSignals({ 
        account_id: currentAccount.id,
        status: 'pending' 
      })
      setSignals(data)
    } catch (error) {
      console.error('获取数据失败:', error)
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchAccountSummary = async () => {
    if (!currentAccount) return
    try {
      const summary = await accountApi.getSummary(currentAccount.id)
      setAccountSummary(summary)
    } catch (error) {
      console.error('获取账户摘要失败:', error)
    }
  }

  useEffect(() => {
    if (currentAccount) {
      fetchData()
      fetchAccountSummary()
    }
  }, [currentAccount])

  const handleApproveSignal = async (id, approved, quantity = null) => {
    try {
      await strategyApi.approveSignal(id, { approved, notes: '', quantity })
      message.success(approved ? '已同意执行' : '已拒绝')
      fetchData()
      fetchAccountSummary()
      refreshPendingCount()
    } catch (error) {
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail)
      } else {
        message.error('操作失败')
      }
    }
  }

  const showApproveModal = (record) => {
    setApprovingSignal(record)
    setApproveQuantity(record.suggested_quantity || 100)
    setApproveModalVisible(true)
  }

  const handleConfirmApprove = () => {
    if (approvingSignal) {
      handleApproveSignal(approvingSignal.id, true, approveQuantity)
      setApproveModalVisible(false)
      setApprovingSignal(null)
    }
  }

  const handleRejectSignal = (record) => {
    Modal.confirm({
      title: '确认拒绝',
      content: `确定要拒绝 ${record.symbol} 的${record.signal_type === 'buy' ? '买入' : '卖出'}信号吗？`,
      okText: '确认拒绝',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => handleApproveSignal(record.id, false)
    })
  }

  const showDetail = (record) => {
    setSelectedSignal(record)
    setDetailModalVisible(true)
  }

  const columns = [
    { 
      title: '资产', 
      key: 'asset', 
      width: 120,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.symbol}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{record.asset_name}</div>
        </div>
      )
    },
    { 
      title: '信号', 
      dataIndex: 'signal_type', 
      key: 'signal_type', 
      width: 80,
      render: (type) => {
        const colorMap = { buy: 'green', sell: 'red' }
        const textMap = { buy: '买入', sell: '卖出' }
        const iconMap = { buy: <RiseOutlined />, sell: <FallOutlined /> }
        return (
          <Tag color={colorMap[type]} icon={iconMap[type]}>
            {textMap[type]}
          </Tag>
        )
      }
    },
    { 
      title: '建议股数', 
      dataIndex: 'suggested_quantity', 
      key: 'suggested_quantity', 
      width: 100,
      render: (v) => <span style={{ fontWeight: 500, color: '#1890ff' }}>{v || 100} 股</span>
    },
    { 
      title: '价格', 
      dataIndex: 'price', 
      key: 'price', 
      width: 100,
      render: (v) => v ? <span style={{ fontWeight: 500 }}>¥{v.toFixed(2)}</span> : '-'
    },
    { 
      title: '预估金额', 
      key: 'estimated_amount', 
      width: 120,
      render: (_, record) => {
        const amount = (record.suggested_quantity || 100) * (record.price || 0)
        return <span style={{ fontWeight: 500, color: '#f50' }}>¥{amount.toFixed(2)}</span>
      }
    },
    { 
      title: '原因', 
      dataIndex: 'reason', 
      key: 'reason', 
      ellipsis: true,
      render: (v) => <Tooltip title={v}>{v}</Tooltip>
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
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => showApproveModal(record)}>
            同意
          </Button>
          <Button size="small" danger icon={<CloseOutlined />} onClick={() => handleRejectSignal(record)}>
            拒绝
          </Button>
          <Button size="small" onClick={() => showDetail(record)}>
            详情
          </Button>
        </Space>
      )
    }
  ]

  if (!currentAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Empty description="请先选择账户" />
      </div>
    )
  }

  const totalAmount = signals.reduce((sum, s) => sum + (s.suggested_quantity || 100) * (s.price || 0), 0)
  const buyCount = signals.filter(s => s.signal_type === 'buy').length
  const sellCount = signals.filter(s => s.signal_type === 'sell').length

  return (
    <div>
      <Card title="审批中心" style={{ marginBottom: 16 }}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic 
              title="待审批总数" 
              value={signals.length} 
              suffix="个"
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="买入信号" 
              value={buyCount} 
              suffix="个"
              valueStyle={{ color: '#52c41a' }}
              prefix={<RiseOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="卖出信号" 
              value={sellCount} 
              suffix="个"
              valueStyle={{ color: '#f5222d' }}
              prefix={<FallOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="预估总金额" 
              value={totalAmount} 
              precision={2}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
        </Row>
        <Table
          columns={columns}
          dataSource={signals}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1000 }}
          locale={{ emptyText: '暂无待审批信号' }}
        />
      </Card>

      <Modal
        title="信号详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedSignal && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="股票代码">{selectedSignal.symbol}</Descriptions.Item>
            <Descriptions.Item label="股票名称">{selectedSignal.asset_name}</Descriptions.Item>
            <Descriptions.Item label="信号类型">
              <Tag color={selectedSignal.signal_type === 'buy' ? 'green' : 'red'}>
                {selectedSignal.signal_type === 'buy' ? '买入' : '卖出'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前价格">¥{selectedSignal.price?.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="建议股数">
              <span style={{ fontWeight: 500, color: '#1890ff', fontSize: 16 }}>
                {selectedSignal.suggested_quantity || 100} 股
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="预估金额">
              <span style={{ fontWeight: 500, color: '#f50', fontSize: 16 }}>
                ¥{((selectedSignal.suggested_quantity || 100) * (selectedSignal.price || 0)).toFixed(2)}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="信号原因" span={2}>
              {selectedSignal.reason}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {new Date(selectedSignal.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="确认执行交易"
        open={approveModalVisible}
        onCancel={() => {
          setApproveModalVisible(false)
          setApprovingSignal(null)
        }}
        onOk={handleConfirmApprove}
        okText="确认执行"
        cancelText="取消"
        width={500}
      >
        {approvingSignal && (
          <div>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="股票代码">{approvingSignal.symbol}</Descriptions.Item>
              <Descriptions.Item label="股票名称">{approvingSignal.asset_name}</Descriptions.Item>
              <Descriptions.Item label="信号类型">
                <Tag color={approvingSignal.signal_type === 'buy' ? 'green' : 'red'}>
                  {approvingSignal.signal_type === 'buy' ? '买入' : '卖出'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="当前价格">¥{approvingSignal.price?.toFixed(2)}</Descriptions.Item>
              {accountSummary && approvingSignal.signal_type === 'buy' && (
                <>
                  <Descriptions.Item label="可用资金">
                    <span style={{ fontWeight: 500, color: '#52c41a' }}>
                      ¥{accountSummary.cash?.toFixed(2)}
                    </span>
                  </Descriptions.Item>
                  <Descriptions.Item label="持仓市值">
                    <span style={{ fontWeight: 500 }}>
                      ¥{accountSummary.position_value?.toFixed(2)}
                    </span>
                  </Descriptions.Item>
                </>
              )}
            </Descriptions>
            
            {approvingSignal.signal_type === 'buy' && accountSummary && 
              (approveQuantity || 0) * (approvingSignal.price || 0) > accountSummary.cash && (
              <Alert
                message="资金不足警告"
                description={`所需金额 ¥${((approveQuantity || 0) * (approvingSignal.price || 0)).toFixed(2)} 超过可用资金 ¥${accountSummary.cash?.toFixed(2)}`}
                type="error"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginBottom: 16 }}
              />
            )}
            
            <Form layout="vertical">
              <Form.Item 
                label={
                  <span>
                    交易股数 
                    <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
                      (建议: {approvingSignal.suggested_quantity || 100} 股)
                    </span>
                  </span>
                }
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={100}
                  max={1000000}
                  step={100}
                  value={approveQuantity}
                  onChange={(value) => setApproveQuantity(value)}
                  addonAfter="股"
                />
              </Form.Item>
              
              <Form.Item label="预估交易金额">
                <span style={{ fontSize: 18, fontWeight: 500, color: '#f50' }}>
                  ¥{((approveQuantity || 0) * (approvingSignal.price || 0)).toFixed(2)}
                </span>
                {accountSummary && approvingSignal.signal_type === 'buy' && (
                  <span style={{ marginLeft: 16, color: '#999' }}>
                    (可用: ¥{accountSummary.cash?.toFixed(2)})
                  </span>
                )}
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ApprovalCenter
