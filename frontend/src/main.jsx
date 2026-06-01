import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  CheckCircle2,
  Package,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Trash2,
  Users,
  LogOut,
  X,
} from 'lucide-react';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'yourinventory-token';
const USER_KEY = 'yourinventory-user';
const DEMO_EMAIL = 'kaushal.dagur@inventory.com';
const DEMO_PASSWORD = 'kaushal123';
const PAGES = ['dashboard', 'products', 'customers', 'orders'];

function getStoredSession() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    return token && user ? { token, user } : null;
  } catch {
    return null;
  }
}

function saveSession(auth) {
  localStorage.setItem(TOKEN_KEY, auth.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function getHashPage() {
  const hashPage = window.location.hash.replace('#', '') || 'dashboard';
  return PAGES.includes(hashPage) ? hashPage : 'dashboard';
}

async function api(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 401) {
    clearSession();
    throw new Error('Session expired. Please sign in again.');
  }

  if (!response.ok) {
    let message = 'Request failed';
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(', ') : message);
  }

  if (response.status === 204) return null;
  return response.json();
}

function App() {
  const [page, setPage] = useState(getHashPage);
  const [searchTerm, setSearchTerm] = useState('');
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [dashboard, setDashboard] = useState({ total_products: 0, total_customers: 0, total_orders: 0, low_stock_products: 0 });
  const [notice, setNotice] = useState(null);
  const [modal, setModal] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [session, setSession] = useState(getStoredSession);

  const loadData = async () => {
    const [productData, customerData, orderData, dashboardData] = await Promise.all([
      api('/products'),
      api('/customers'),
      api('/orders'),
      api('/dashboard'),
    ]);
    setProducts(productData);
    setCustomers(customerData);
    setOrders(orderData);
    setDashboard(dashboardData);
  };

  useEffect(() => {
    const onHashChange = () => setPage(getHashPage());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (!session) return;
    loadData().catch((error) => setNotice({ type: 'error', message: error.message }));
  }, [session]);

  const signIn = async (credentials) => {
    const auth = await api('/auth/login', { method: 'POST', body: JSON.stringify(credentials) });
    saveSession(auth);
    setSession({ token: auth.access_token, user: auth.user });
    setNotice({ type: 'success', message: 'Signed in successfully' });
  };

  const signOut = () => {
    clearSession();
    setSession(null);
    setProducts([]);
    setCustomers([]);
    setOrders([]);
    setDashboard({ total_products: 0, total_customers: 0, total_orders: 0, low_stock_products: 0 });
    setNotice({ type: 'success', message: 'Signed out' });
  };

  const runAction = async (successMessage, action) => {
    try {
      await action();
      await loadData();
      setModal(null);
      setNotice({ type: 'success', message: successMessage });
    } catch (error) {
      setNotice({ type: 'error', message: error.message });
    }
  };

  const totalStock = useMemo(() => products.reduce((sum, product) => sum + product.quantity_in_stock, 0), [products]);
  const totalRevenue = useMemo(() => orders.reduce((sum, order) => sum + Number(order.total_amount), 0), [orders]);
  const lowStock = useMemo(() => products.filter((product) => product.quantity_in_stock <= 5), [products]);
  const productSales = useMemo(() => {
    const sales = new Map();
    orders.forEach((order) => {
      order.items.forEach((item) => {
        const current = sales.get(item.product_id) || { name: item.product.name, quantity: 0 };
        current.quantity += item.quantity;
        sales.set(item.product_id, current);
      });
    });
    return Array.from(sales.values()).sort((a, b) => b.quantity - a.quantity);
  }, [orders]);
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredProducts = useMemo(
    () => products.filter((product) => [product.name, product.sku].some((value) => value.toLowerCase().includes(normalizedSearch))),
    [products, normalizedSearch],
  );
  const filteredCustomers = useMemo(
    () => customers.filter((customer) => [customer.full_name, customer.email, customer.phone_number].some((value) => value.toLowerCase().includes(normalizedSearch))),
    [customers, normalizedSearch],
  );
  const filteredOrders = useMemo(
    () => orders.filter((order) => [
      String(order.id),
      order.customer.full_name,
      order.customer.email,
      String(order.total_amount),
      ...order.items.map((item) => item.product.name),
      ...order.items.map((item) => item.product.sku),
    ].join(' ').toLowerCase().includes(normalizedSearch)),
    [orders, normalizedSearch],
  );

  if (!session) {
    return (
      <>
        {notice && (
          <div className={`notice ${notice.type}`}>
            {notice.type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span>{notice.message}</span>
            <button type="button" aria-label="Dismiss message" onClick={() => setNotice(null)}><X size={14} /></button>
          </div>
        )}
        <LoginScreen onSignIn={signIn} onError={(message) => setNotice({ type: 'error', message })} />
      </>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar page={page} user={session.user} onSignOut={signOut} />
      <main className="workspace-shell">
        <PageHeader
          page={page}
          onRefresh={() => loadData()}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
        />

        {notice && (
          <div className={`notice ${notice.type}`}>
            {notice.type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span>{notice.message}</span>
            <button type="button" aria-label="Dismiss message" onClick={() => setNotice(null)}><X size={14} /></button>
          </div>
        )}

        {page === 'dashboard' && (
          <DashboardPage
            dashboard={dashboard}
            totalStock={totalStock}
            totalRevenue={totalRevenue}
            productSales={productSales}
            lowStock={lowStock}
            products={products}
            orders={orders}
            searchTerm={normalizedSearch}
          />
        )}
        {page === 'products' && (
          <ProductsPage products={filteredProducts} onAdd={() => setModal('product')} runAction={runAction} />
        )}
        {page === 'customers' && (
          <CustomersPage customers={filteredCustomers} onAdd={() => setModal('customer')} runAction={runAction} />
        )}
        {page === 'orders' && (
          <OrdersPage
            orders={filteredOrders}
            products={products}
            customers={customers}
            selectedOrder={selectedOrder}
            setSelectedOrder={setSelectedOrder}
            onAdd={() => setModal('order')}
            runAction={runAction}
          />
        )}
      </main>
      {modal === 'product' && <ProductModal onClose={() => setModal(null)} runAction={runAction} />}
      {modal === 'customer' && <CustomerModal onClose={() => setModal(null)} runAction={runAction} />}
      {modal === 'order' && <OrderModal onClose={() => setModal(null)} runAction={runAction} products={products} customers={customers} />}
    </div>
  );
}

function LoginScreen({ onSignIn, onError }) {
  const [form, setForm] = useState({ email: DEMO_EMAIL, password: DEMO_PASSWORD });
  const [authNotice, setAuthNotice] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    try {
      await onSignIn({ email: form.email, password: form.password });
    } catch (error) {
      setAuthNotice({ type: 'error', message: error.message });
      onError(error.message);
    }
  };

  return (
    <main className="login-screen">
      <div className="login-card">
        <section className="login-accent" aria-hidden="true">
          <div className="login-accent-pattern" />
          <BrandMark variant="login" />
        </section>
        <section className="login-form-side">
          <form onSubmit={submit} className="auth-card">
            <h2>Log in</h2>
            <p className="auth-lead">Sign in to manage your inventory and orders.</p>
            {authNotice && (
              <div className={`notice ${authNotice.type}`}>
                <span>{authNotice.message}</span>
              </div>
            )}
            <label>
              <span>Email</span>
              <input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </label>
            <label>
              <span>Password</span>
              <input required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
            </label>
            <button type="submit">Sign in</button>
          </form>
          <div className="credentials-box">
            <strong>Login credentials</strong>
            <span>Email: {DEMO_EMAIL}</span>
            <span>Password: {DEMO_PASSWORD}</span>
          </div>
        </section>
      </div>
    </main>
  );
}

function BrandMark({ variant = 'app' }) {
  return (
    <div className={`brand-lockup ${variant === 'login' ? 'brand-lockup-login' : ''}`}>
      <div className="brand-icon"><Boxes size={24} /></div>
      <div>
        <strong>yourinventory</strong>
        {variant !== 'login' && <span>Inventory & Orders</span>}
      </div>
    </div>
  );
}

function Sidebar({ page, user, onSignOut }) {
  const links = [
    { id: 'dashboard', label: 'Dashboard', icon: <BarChart3 size={18} /> },
    { id: 'products', label: 'Products', icon: <Package size={18} /> },
    { id: 'customers', label: 'Customers', icon: <Users size={18} /> },
    { id: 'orders', label: 'Orders', icon: <ShoppingCart size={18} /> },
  ];

  return (
    <aside className="app-sidebar">
      <BrandMark />
      <nav>
        <span>Menu</span>
        {links.map((link) => (
          <a className={page === link.id ? 'active' : ''} href={`#${link.id}`} key={link.id}>
            {link.icon}{link.label}
          </a>
        ))}
      </nav>
      <div className="admin-card">
        <div className="admin-avatar">{user.full_name?.charAt(0).toUpperCase() || 'U'}</div>
        <div>
          <strong>{user.full_name}</strong>
          <span>{user.email}</span>
        </div>
      </div>
      <button className="signout" type="button" onClick={onSignOut}><LogOut size={17} />Sign out</button>
    </aside>
  );
}

function PageHeader({ page, onRefresh, searchTerm, setSearchTerm }) {
  const content = {
    dashboard: ['Dashboard', 'Live overview of your inventory & orders', 'Search'],
    products: ['Products', 'Manage your catalog & inventory', 'Search name or SKU'],
    customers: ['Customers', 'Manage your customer directory', 'Search name, email, phone'],
    orders: ['Orders', 'Create and monitor customer orders', 'Search order or customer'],
  }[page] || ['Dashboard', 'Live overview of your inventory & orders', ''];

  return (
    <header className={`page-header ${page === 'dashboard' ? 'dashboard-header' : ''}`}>
      <div>
        <h1>{content[0]}</h1>
        <p>{content[1]}</p>
      </div>
      <div className="header-actions">
        {content[2] && (
          <label className="header-search">
            <Search size={18} />
            <input placeholder={content[2]} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </label>
        )}
        <button className="ghost-icon" type="button" aria-label="Refresh data" onClick={onRefresh}><RefreshCw size={18} /></button>
      </div>
    </header>
  );
}

function DashboardPage({ dashboard, totalStock, totalRevenue, productSales, lowStock, products }) {
  const unitsSold = productSales.reduce((sum, item) => sum + item.quantity, 0);
  const unitsInStock = totalStock;
  const totalUnits = unitsSold + unitsInStock || 1;
  const stockPercent = Math.round((unitsInStock / totalUnits) * 100);
  const soldPercent = 100 - stockPercent;
  const topSales = productSales.length
    ? productSales.slice(0, 10)
    : products.slice(0, 10).map((product) => ({ name: product.name, quantity: product.quantity_in_stock }));

  return (
    <div className="page-body dashboard-page">
      <section className="overview-panel">
        <h2>Overview</h2>
        <div className="stat-grid dashboard-stat-grid">
          <StatCard label="Total Products" value={dashboard.total_products} hint="Items in catalog" icon={<Package />} tone="mint" />
          <StatCard label="Total Customers" value={dashboard.total_customers} hint="Registered buyers" icon={<Users />} tone="mint" />
          <StatCard label="Total Orders" value={dashboard.total_orders} hint="Orders placed" icon={<Boxes />} tone="mint" />
          <StatCard label="Low Stock" value={dashboard.low_stock_products} hint="Products with stock ≤ 5" icon={<AlertTriangle />} tone="peach" />
        </div>
      </section>

      <section className="dashboard-reference-grid">
        <div className="chart-card inventory-values-card">
          <h2>Inventory split</h2>
          <p className="chart-subtitle">{unitsInStock} in stock · {unitsSold} sold</p>
          <div className="inventory-chart-row">
            <div className="pie-chart" style={{ '--stock': `${stockPercent}%` }}>
              <span>{stockPercent}%</span>
              <small>in stock</small>
            </div>
            <div className="pie-legend">
              <span><i className="legend-stock" /> In stock ({unitsInStock})</span>
              <span><i className="legend-sold" /> Sold ({unitsSold})</span>
            </div>
          </div>
        </div>

        <div className="chart-card top-sales-card">
          <h2>Top 10 Products by sales</h2>
          {topSales.length ? <BarList items={topSales} /> : <EmptyState label="No sales yet" />}
        </div>

        <div className="chart-card profit-card">
          <div className="profit-heading">
            <h2>Revenue overview</h2>
            <span>Based on your order totals</span>
          </div>
          <div className="profit-chart">
            <div className="profit-grid">
              <span>High</span><span>Mid</span><span>Low</span>
              <svg viewBox="0 0 640 220" preserveAspectRatio="none" aria-hidden="true">
                <path className="profit-area" d="M0 105 C60 130 88 125 130 118 C175 108 188 60 238 82 C292 105 316 126 370 92 C428 54 475 92 525 63 C570 36 608 42 640 20 L640 220 L0 220 Z" />
                <path className="profit-line-main" d="M0 105 C60 130 88 125 130 118 C175 108 188 60 238 82 C292 105 316 126 370 92 C428 54 475 92 525 63 C570 36 608 42 640 20" />
              </svg>
            </div>
            <p className="helper-note">Total revenue: ${Number(totalRevenue).toFixed(2)}</p>
          </div>
        </div>

        <div className="chart-card low-stock-card">
          <h2>Low Stock Alerts</h2>
          <p>Items at or below threshold</p>
          {lowStock.length ? (
            <div className="simple-list">{lowStock.map((product) => <span key={product.id}>{product.name}<b>{product.quantity_in_stock}</b></span>)}</div>
          ) : <EmptyState label={products.length ? 'No low stock alerts' : 'No products yet'} />}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, hint, icon, tone }) {
  return (
    <div className="stat-card">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <p>{hint}</p>
      </div>
      <i className={tone}>{icon}</i>
    </div>
  );
}

function ProductsPage({ products, onAdd, runAction }) {
  const [editingProduct, setEditingProduct] = useState(null);

  return (
    <div className="page-body">
      <ListHeader kicker="Catalog" title={`${products.length} products`} onAdd={onAdd} label="Add product" />
      <DataTable headers={['Product', 'SKU', 'Price', 'Stock', 'Actions']} empty="No products yet. Click Add product to create one.">
        {products.map((product) => (
          <tr key={product.id}>
            <td><strong>{product.name}</strong></td>
            <td>{product.sku}</td>
            <td>${Number(product.price).toFixed(2)}</td>
            <td>{product.quantity_in_stock}</td>
            <td className="actions">
              <button type="button" onClick={() => setEditingProduct(product)}>Edit</button>
              <button type="button" aria-label="Delete product" onClick={() => runAction('Product deleted', () => api(`/products/${product.id}`, { method: 'DELETE' }))}><Trash2 size={16} /></button>
            </td>
          </tr>
        ))}
      </DataTable>
      {editingProduct && <ProductModal product={editingProduct} onClose={() => setEditingProduct(null)} runAction={runAction} />}
    </div>
  );
}

function CustomersPage({ customers, onAdd, runAction }) {
  return (
    <div className="page-body">
      <ListHeader kicker="Directory" title={`${customers.length} customers`} onAdd={onAdd} label="Add customer" />
      <DataTable headers={['Name', 'Email', 'Phone', 'Actions']} empty="No customers yet.">
        {customers.map((customer) => (
          <tr key={customer.id}>
            <td><strong>{customer.full_name}</strong></td>
            <td>{customer.email}</td>
            <td>{customer.phone_number}</td>
            <td className="actions">
              <button type="button" aria-label="Delete customer" onClick={() => runAction('Customer deleted', () => api(`/customers/${customer.id}`, { method: 'DELETE' }))}><Trash2 size={16} /></button>
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

function OrdersPage({ orders, products, customers, selectedOrder, setSelectedOrder, onAdd, runAction }) {
  return (
    <div className="page-body">
      <ListHeader kicker="Order desk" title={`${orders.length} orders`} onAdd={onAdd} label="Add order" />
      <DataTable headers={['Order', 'Customer', 'Items', 'Total', 'Actions']} empty="No orders yet.">
        {orders.map((order) => (
          <tr key={order.id}>
            <td><strong>#{order.id}</strong></td>
            <td>{order.customer.full_name}</td>
            <td>{order.items.reduce((sum, item) => sum + item.quantity, 0)}</td>
            <td>${Number(order.total_amount).toFixed(2)}</td>
            <td className="actions">
              <button type="button" onClick={() => setSelectedOrder(order)}>Details</button>
              <button type="button" aria-label="Delete order" onClick={() => runAction('Order deleted', () => api(`/orders/${order.id}`, { method: 'DELETE' }))}><Trash2 size={16} /></button>
            </td>
          </tr>
        ))}
      </DataTable>
      {selectedOrder && (
        <div className="detail-card">
          <button type="button" aria-label="Close order details" onClick={() => setSelectedOrder(null)}><X size={16} /></button>
          <h2>Order #{selectedOrder.id}</h2>
          <p>{selectedOrder.customer.full_name} · ${Number(selectedOrder.total_amount).toFixed(2)}</p>
          {selectedOrder.items.map((item) => (
            <span key={item.id}>{item.product.name} × {item.quantity} = ${Number(item.line_total).toFixed(2)}</span>
          ))}
        </div>
      )}
      {!products.length || !customers.length ? (
        <p className="helper-note">Create at least one product and one customer before placing an order.</p>
      ) : null}
    </div>
  );
}

function ListHeader({ kicker, title, onAdd, label }) {
  return (
    <div className="list-header">
      <div>
        <span>{kicker}</span>
        <h2>{title}</h2>
      </div>
      <button type="button" onClick={onAdd}><Plus size={18} />{label}</button>
    </div>
  );
}

function ProductModal({ product, onClose, runAction }) {
  const [form, setForm] = useState(product || { name: '', sku: '', price: '', quantity_in_stock: '' });

  const submit = (event) => {
    event.preventDefault();
    const payload = { ...form, price: Number(form.price), quantity_in_stock: Number(form.quantity_in_stock) };
    runAction(product ? 'Product updated' : 'Product created', () => api(product ? `/products/${product.id}` : '/products', {
      method: product ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    }));
  };

  return (
    <Modal title={product ? 'Edit product' : 'Add product'} onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <input required placeholder="Product name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <input required placeholder="SKU/code" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} />
        <input required type="number" min="0.01" step="0.01" placeholder="Price" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} />
        <input required type="number" min="0" placeholder="Stock quantity" value={form.quantity_in_stock} onChange={(event) => setForm({ ...form, quantity_in_stock: event.target.value })} />
        <button type="submit">{product ? 'Save product' : 'Create product'}</button>
      </form>
    </Modal>
  );
}

function CustomerModal({ onClose, runAction }) {
  const [form, setForm] = useState({ full_name: '', email: '', phone_number: '' });

  const submit = (event) => {
    event.preventDefault();
    runAction('Customer created', () => api('/customers', { method: 'POST', body: JSON.stringify(form) }));
  };

  return (
    <Modal title="Add customer" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <input required placeholder="Full name" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
        <input required type="email" placeholder="Email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        <input required placeholder="Phone number" value={form.phone_number} onChange={(event) => setForm({ ...form, phone_number: event.target.value })} />
        <button type="submit">Create customer</button>
      </form>
    </Modal>
  );
}

function OrderModal({ products, customers, onClose, runAction }) {
  const [form, setForm] = useState({ customer_id: '', product_id: '', quantity: 1 });

  const submit = (event) => {
    event.preventDefault();
    runAction('Order created and inventory updated', () => api('/orders', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: Number(form.customer_id),
        items: [{ product_id: Number(form.product_id), quantity: Number(form.quantity) }],
      }),
    }));
  };

  return (
    <Modal title="Add order" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <select required value={form.customer_id} onChange={(event) => setForm({ ...form, customer_id: event.target.value })}>
          <option value="">Select customer</option>
          {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.full_name}</option>)}
        </select>
        <select required value={form.product_id} onChange={(event) => setForm({ ...form, product_id: event.target.value })}>
          <option value="">Select product</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name} ({product.quantity_in_stock} in stock)</option>)}
        </select>
        <input required type="number" min="1" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
        <button type="submit">Create order</button>
      </form>
    </Modal>
  );
}

function Modal({ title, children, onClose }) {
  return (
    <div className="modal-backdrop">
      <section className="modal-card">
        <header>
          <h2>{title}</h2>
          <button type="button" aria-label="Close modal" onClick={onClose}><X size={18} /></button>
        </header>
        {children}
      </section>
    </div>
  );
}

function BarList({ items }) {
  const max = Math.max(...items.map((item) => item.quantity), 1);
  return (
    <div className="bar-list">
      {items.map((item) => (
        <div className="bar-row" key={item.name}>
          <span>{item.name}</span>
          <div><i style={{ width: `${Math.max((item.quantity / max) * 100, 9)}%` }} /></div>
          <b>{item.quantity}</b>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ label }) {
  return <div className="empty-state">{label}</div>;
}

function DataTable({ headers, children, empty }) {
  const hasRows = React.Children.count(children) > 0;
  return (
    <div className="data-card">
      <table>
        <thead>
          <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
        </thead>
        <tbody>
          {hasRows ? children : (
            <tr>
              <td className="empty-cell" colSpan={headers.length}>{empty}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
