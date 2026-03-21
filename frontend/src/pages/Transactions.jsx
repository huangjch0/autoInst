import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, DatePicker, message, Space, Popconfirm, Tag, Empty } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { accountApi, assetApi, transactionApi } from '../api'
import { useAccount } from '../App'

const { Option } = Select
const { TextArea } = Input

function Transactions() {
  const { currentAccount } = useAccount()
  const [transactions, setTransactions] = useState([])
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTransaction, setEditingTransaction] = useState(null)
  const [form] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    if (currentAccount) {
      fetchData()
    }
  }, [currentAccount, filters])

  useEffect(() => {
    fetchAssets()
  }, [])

  const fetchAssets = async () => {
    try {
      const data = await assetApi.getAll()
      setAssets(data)
    } catch (error) {
      message.error('获取资产列表失败')
    }
  }

  const fetchData = async () => {
    if (!currentAccount) return
    
    setLoading(true)
    try {
      const transData = await accountApi.getTransactions(currentAccount.id, filters)
      setTransactions(transData)
    } catch (error) {
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    if (!currentAccount) {
      message.warning('请先选择账户')
      return
    }
    setEditingTransaction(null)
    form.resetFields()
    form.setFieldsValue({ date: dayjs() })
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingTransaction(record)
    form.setFieldsValue({
      ...record,
      date: dayjs(record.date)
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await transactionApi.delete(id)
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
        asset_id: values.asset_id,
        type: values.type,
        date: values.date.toISOString(),
        quantity: values.quantity,
        price: values.price,
        fee: values.fee || 0,
        notes: values.notes
      }
      if (editingTransaction) {
        await transactionApi.update(editingTransaction.id, data)
        message.success('更新成功')
      } else {
        await transactionApi.create(data)
        message.success('添加成功')
      }
      setModalVisible(false)
      fetchData()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const columns = [
    { title: '资产代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '资产名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'type', key: 'type', render: (type) => (
      <Tag color={type === 'buy' ? 'green' : 'red'}>
        {type === 'buy' ? '买入' : '卖出'}
      </Tag>
    )},
    { title: '日期', dataIndex: 'date', key: 'date', render: (v) => new Date(v).toLocaleDateString() },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', render: (v) => v?.toFixed(2) },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v) => `¥${v?.toFixed(2)}` },
    { title: '金额', key: 'amount', render: (_, record) => `¥${(record.quantity * record.price).toFixed(2)}` },
    { title: '手续费', dataIndex: 'fee', key: 'fee', render: (v) => `¥${v?.toFixed(2)}` },
    { title: '备注', dataIndex: 'notes', key: 'notes', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
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

  if (!currentAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Empty description="请先选择账户" />
      </div>
    )
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加交易
        </Button>
        <Select
          style={{ width: 120 }}
          placeholder="交易类型"
          allowClear
          value={filters.transaction_type}
          onChange={(v) => setFilters({ ...filters, transaction_type: v })}
        >
          <Option value="buy">买入</Option>
          <Option value="sell">卖出</Option>
        </Select>
      </Space>

      <Table
        columns={columns}
        dataSource={transactions}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1200 }}
      />

      <Modal
        title={editingTransaction ? '编辑交易' : '添加交易'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="asset_id" label="资产" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children">
              {assets.map(a => (
                <Option key={a.id} value={a.id}>{a.symbol} - {a.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="type" label="交易类型" rules={[{ required: true }]}>
            <Select>
              <Option value="buy">买入</Option>
              <Option value="sell">卖出</Option>
            </Select>
          </Form.Item>
          <Form.Item name="date" label="交易日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="quantity" label="数量" rules={[{ required: true }]}>
            <InputNumber min={0} step={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="price" label="价格" rules={[{ required: true }]}>
            <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="fee" label="手续费">
            <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Transactions
