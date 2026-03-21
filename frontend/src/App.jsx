import React, { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu, Select, Spin, message, Empty, Button, Modal, Form, Input, InputNumber, Badge } from 'antd'
import {
  DashboardOutlined,
  StockOutlined,
  TransactionOutlined,
  LineChartOutlined,
  AccountBookOutlined,
  ExperimentOutlined,
  PlusOutlined,
  AuditOutlined
} from '@ant-design/icons'
import Dashboard from './pages/Dashboard'
import Assets from './pages/Assets'
import Transactions from './pages/Transactions'
import Strategies from './pages/Strategies'
import Backtest from './pages/Backtest'
import Accounts from './pages/Accounts'
import ApprovalCenter from './pages/ApprovalCenter'
import { accountApi } from './api'

const { Header, Sider, Content } = Layout
const { Option } = Select

export const AccountContext = createContext(null)
export const PendingCountContext = createContext(null)

export function useAccount() {
  return useContext(AccountContext)
}

export function usePendingCount() {
  return useContext(PendingCountContext)
}

function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState([])
  const [currentAccount, setCurrentAccount] = useState(null)
  const [loading, setLoading] = useState(true)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const [datasources, setDatasources] = useState({})
  const [form] = Form.useForm()

  useEffect(() => {
    fetchAccounts()
    fetchDatasources()
  }, [])

  useEffect(() => {
    if (accounts.length > 0 && !currentAccount) {
      const savedAccountId = localStorage.getItem('currentAccountId')
      const savedAccount = accounts.find(a => a.id === parseInt(savedAccountId))
      setCurrentAccount(savedAccount || accounts[0])
    }
  }, [accounts])

  useEffect(() => {
    if (currentAccount) {
      localStorage.setItem('currentAccountId', currentAccount.id.toString())
      fetchPendingCount()
    }
  }, [currentAccount])

  const fetchAccounts = async () => {
    setLoading(true)
    try {
      const data = await accountApi.getAll()
      setAccounts(data)
      if (data.length > 0) {
        const savedAccountId = localStorage.getItem('currentAccountId')
        const savedAccount = data.find(a => a.id === parseInt(savedAccountId))
        setCurrentAccount(savedAccount || data[0])
      }
    } catch (error) {
      message.error('获取账户列表失败')
    } finally {
      setLoading(false)
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

  const fetchPendingCount = async () => {
    try {
      const response = await fetch(`/api/strategies/list/signals?status=pending&account_id=${currentAccount?.id}`)
      const data = await response.json()
      setPendingCount(data.length)
    } catch (error) {
      console.error('获取待审批数量失败:', error)
    }
  }

  const handleAccountChange = (accountId) => {
    const account = accounts.find(a => a.id === accountId)
    setCurrentAccount(account)
  }

  const handleCreateAccount = async () => {
    try {
      const values = await form.validateFields()
      const newAccount = await accountApi.create(values)
      message.success('账户创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      await fetchAccounts()
      setCurrentAccount(newAccount)
    } catch (error) {
      message.error('创建账户失败')
    }
  }

  const handleClick = (e) => {
    navigate(e.key)
  }

  const getMenuItems = () => {
    const items = [
      { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
      { key: '/approval', icon: <Badge count={pendingCount} size="small"><AuditOutlined /></Badge>, label: '审批中心' },
      { key: '/assets', icon: <StockOutlined />, label: '资产管理' },
      { key: '/transactions', icon: <TransactionOutlined />, label: '交易记录' },
      { key: '/strategies', icon: <LineChartOutlined />, label: '策略管理' },
      { key: '/backtest', icon: <ExperimentOutlined />, label: '策略回测' },
      { key: '/accounts', icon: <AccountBookOutlined />, label: '账户管理' }
    ]
    return items
  }

  const isAccountsPage = location.pathname === '/accounts'

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (accounts.length === 0 && !isAccountsPage) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <Empty description="请先创建账户" style={{ marginBottom: 24 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          创建账户
        </Button>
        <Modal
          title="创建账户"
          open={createModalVisible}
          onOk={handleCreateAccount}
          onCancel={() => setCreateModalVisible(false)}
        >
          <Form form={form} layout="vertical">
            <Form.Item name="name" label="账户名称" rules={[{ required: true, message: '请输入账户名称' }]}>
              <Input placeholder="如: 主账户、融资账户" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={2} placeholder="账户说明" />
            </Form.Item>
            <Form.Item name="initial_capital" label="初始资金" initialValue={100000}>
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
      </div>
    )
  }

  return (
    <AccountContext.Provider value={{ currentAccount, accounts, refreshAccounts: fetchAccounts }}>
      <PendingCountContext.Provider value={{ pendingCount, refreshPendingCount: fetchPendingCount }}>
        <Layout style={{ minHeight: '100vh' }}>
          <Sider width={200} style={{ background: '#fff' }}>
            <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 'bold' }}>
              投资系统
            </div>
            <Menu
              mode="inline"
              selectedKeys={[location.pathname]}
              items={getMenuItems()}
              onClick={handleClick}
              style={{ height: 'calc(100% - 64px)', borderRight: 0 }}
            />
          </Sider>
          <Layout>
            <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0 }}>自动化投资系统</h2>
              {accounts.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>当前账户:</span>
                  <Select
                    value={currentAccount?.id}
                    onChange={handleAccountChange}
                    style={{ width: 200 }}
                  >
                    {accounts.map(a => (
                      <Option key={a.id} value={a.id}>{a.name}</Option>
                    ))}
                  </Select>
                  <Button 
                    type="link" 
                    icon={<PlusOutlined />}
                    onClick={() => setCreateModalVisible(true)}
                  >
                    新建
                  </Button>
                </div>
              )}
            </Header>
            <Content style={{ margin: '24px', background: '#fff', padding: '24px', borderRadius: '8px' }}>
              {isAccountsPage || currentAccount ? (
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/approval" element={<ApprovalCenter />} />
                  <Route path="/assets" element={<Assets />} />
                  <Route path="/transactions" element={<Transactions />} />
                  <Route path="/strategies" element={<Strategies />} />
                  <Route path="/backtest" element={<Backtest />} />
                  <Route path="/accounts" element={<Accounts />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              ) : (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Empty description="请先选择或创建账户" />
                </div>
              )}
            </Content>
          </Layout>
        </Layout>

        <Modal
          title="创建账户"
          open={createModalVisible}
          onOk={handleCreateAccount}
          onCancel={() => setCreateModalVisible(false)}
        >
          <Form form={form} layout="vertical">
            <Form.Item name="name" label="账户名称" rules={[{ required: true, message: '请输入账户名称' }]}>
              <Input placeholder="如: 主账户、融资账户" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={2} placeholder="账户说明" />
            </Form.Item>
            <Form.Item name="initial_capital" label="初始资金" initialValue={100000}>
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
      </PendingCountContext.Provider>
    </AccountContext.Provider>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}

export default App
