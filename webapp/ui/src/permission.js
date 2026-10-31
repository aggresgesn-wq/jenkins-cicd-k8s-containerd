import router from './router'
import store from './store'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { isRelogin } from '@/utils/request'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login', '/auth-redirect', '/bind', '/register']

router.beforeEach(async (to, from, next) => {
  NProgress.start()
  to.meta.title && store.dispatch('settings/setTitle', to.meta.title)

  // 免登录白名单
  if (whiteList.indexOf(to.path) !== -1) {
    if (to.path === '/login' && store.getters.roles.length > 0) {
      next({ path: '/' })
      NProgress.done()
      return
    }
    next()
    return
  }

  if (store.getters.roles.length > 0) {
    next()
    return
  }

  // 会话有效性以服务端为准：拉取用户信息失败（HTTP 401）即跳转登录页
  isRelogin.show = true
  try {
    await store.dispatch('GetInfo')
    const accessRoutes = await store.dispatch('GenerateRoutes')
    router.addRoutes(accessRoutes)
    isRelogin.show = false
    next({ ...to, replace: true })
  } catch (e) {
    isRelogin.show = false
    await store.dispatch('FedLogOut')
    next(`/login?redirect=${to.fullPath}`)
    NProgress.done()
  }
})

router.afterEach(() => {
  NProgress.done()
})
