import {
  createBackendDeveloperRootCauseOption,
  createDefectReqRateOption,
  createDeveloperRootCauseOption,
  createFrontendDeveloperRootCauseOption,
  createProductManagerRootCauseOption,
  createProductRootCauseOption,
  createReqDeveloperOption,
  createReqGroupOption,
  createReqPriorityStatusOption,
  createReqPriorityTypeOption,
  createReqProductManagerOption,
  createReqTesterWorkloadOption,
  createRequirementDefectsOption,
  createRequirementRootCauseResponsibilityOption,
  createRootCauseResponsibilityOption,
  createTesterPersonRootCauseOption,
  createTesterRootCauseOption,
  createTestcaseTesterOption
} from './chartOptions'

export const chartOptionFactories = {
  'requirement-defects': createRequirementDefectsOption,
  'root-cause-responsibility': createRootCauseResponsibilityOption,
  'requirement-root-cause-responsibility': createRequirementRootCauseResponsibilityOption,
  'product-root-cause': createProductRootCauseOption,
  'developer-root-cause': createDeveloperRootCauseOption,
  'tester-root-cause': createTesterRootCauseOption,
  'product-manager-root-cause': createProductManagerRootCauseOption,
  'frontend-developer-root-cause': createFrontendDeveloperRootCauseOption,
  'backend-developer-root-cause': createBackendDeveloperRootCauseOption,
  'tester-person-root-cause': createTesterPersonRootCauseOption,
  'req-priority-status': createReqPriorityStatusOption,
  'req-priority-type': createReqPriorityTypeOption,
  'req-group': createReqGroupOption,
  'req-product-manager': createReqProductManagerOption,
  'req-developer': createReqDeveloperOption,
  'req-tester-workload': createReqTesterWorkloadOption,
  'testcase-tester': createTestcaseTesterOption,
  'defect-req-rate': createDefectReqRateOption
}

export const coreCharts = [
  { id: 'chart1', endpoint: 'requirement-defects', title: '需求缺陷数统计', description: '按 JIRA 任务编码统计需求对应的缺陷数量' },
  { id: 'chart2', endpoint: 'root-cause-responsibility', title: '根因类型 VS 责任方', description: '查看各类根因在责任方上的分布情况' },
  { id: 'chart3', endpoint: 'requirement-root-cause-responsibility', title: '需求 VS 根因 VS 责任方', description: '识别问题需求及其责任方分布' },
  { id: 'chart4', endpoint: 'product-root-cause', title: '根因 VS 产品', description: '聚焦产品侧缺陷的根因归属' },
  { id: 'chart7', endpoint: 'product-manager-root-cause', title: '产品经理 VS 根因', description: '结合需求清单查看产品经理维度问题' },
  { id: 'chart5', endpoint: 'developer-root-cause', title: '根因 VS 开发', description: '按前后端开发维度统计根因分布' },
  { id: 'chart8', endpoint: 'frontend-developer-root-cause', title: '前端开发 VS 根因', description: '聚焦前端开发相关问题' },
  { id: 'chart9', endpoint: 'backend-developer-root-cause', title: '后端开发 VS 根因', description: '聚焦后端开发相关问题' },
  { id: 'chart6', endpoint: 'tester-root-cause', title: '根因 VS 测试', description: '从测试侧观察根因分布' },
  { id: 'chart10', endpoint: 'tester-person-root-cause', title: '测试人员 VS 根因', description: '精确到测试人员的根因分布' }
]

export const requirementCharts = [
  { id: 'req_chart1', endpoint: 'req-priority-status', title: '需求优先级 VS 状态' },
  { id: 'req_chart2', endpoint: 'req-priority-type', title: '需求优先级 VS 类型' },
  { id: 'req_chart3', endpoint: 'req-group', title: '组别 VS 需求' },
  { id: 'req_chart4', endpoint: 'req-product-manager', title: '产品经理 VS 需求' },
  { id: 'req_chart5', endpoint: 'req-developer', title: '前后端开发 VS 需求' },
  { id: 'req_chart6', endpoint: 'req-tester-workload', title: '测试人员 VS 需求 VS 测试工时' }
]

export const testcaseCharts = [
  { id: 'tc_chart1', endpoint: 'testcase-tester', title: '测试人员 VS 测试用例执行' }
]

export const combinedCharts = [
  { id: 'combined_chart1', endpoint: 'defect-req-rate', title: '缺陷需求率统计' }
]

export const shareCharts = [
  { id: 'share_chart1', endpoint: 'requirement-defects', title: '需求缺陷数统计' },
  { id: 'share_chart2', endpoint: 'root-cause-responsibility', title: '根因类型 VS 责任方' },
  { id: 'share_chart3', endpoint: 'requirement-root-cause-responsibility', title: '需求 VS 根因 VS 责任方' },
  { id: 'share_chart4', endpoint: 'product-root-cause', title: '根因 VS 产品' },
  { id: 'share_chart5', endpoint: 'developer-root-cause', title: '根因 VS 开发' },
  { id: 'share_chart6', endpoint: 'tester-root-cause', title: '根因 VS 测试' }
]
