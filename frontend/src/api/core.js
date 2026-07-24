/**
 * 核心功能模块相关 API
 */
import request from '@/utils/api'

// ==================== 统一通知配置 ====================

// 获取所有通知配置
export function getUnifiedNotificationConfigs(params) {
  return request({
    url: '/core/notification-configs/',
    method: 'get',
    params
  })
}

// 获取通知配置详情
export function getUnifiedNotificationConfigDetail(id) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'get'
  })
}

// 创建通知配置
export function createUnifiedNotificationConfig(data) {
  return request({
    url: '/core/notification-configs/',
    method: 'post',
    data
  })
}

// 更新通知配置
export function updateUnifiedNotificationConfig(id, data) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'put',
    data
  })
}

// 删除通知配置
export function deleteUnifiedNotificationConfig(id) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'delete'
  })
}

// 设置为默认配置
export function setDefaultNotificationConfig(id) {
  return request({
    url: `/core/notification-configs/${id}/set_default/`,
    method: 'post'
  })
}

// 获取所有启用的配置
export function getActiveNotificationConfigs() {
  return request({
    url: '/core/notification-configs/active_configs/',
    method: 'get'
  })
}

// 测试授权连接
export function testAuthorizedNotificationConnection(id, data) {
  return request({
    url: `/core/notification-configs/${id}/test_authorized_connection/`,
    method: 'post',
    data
  })
}

// 发起三方 OAuth 授权
export function startAuthorizedNotificationOAuth(id, data) {
  return request({
    url: `/core/notification-configs/${id}/start_authorized_oauth/`,
    method: 'post',
    data
  })
}

// 断开授权连接
export function disconnectAuthorizedNotificationConnection(id, data) {
  return request({
    url: `/core/notification-configs/${id}/disconnect_authorized_connection/`,
    method: 'post',
    data
  })
}

// 获取授权连接状态
export function getAuthorizedNotificationConnectionStatus(id, params) {
  return request({
    url: `/core/notification-configs/${id}/authorized_connection_status/`,
    method: 'get',
    params
  })
}
