'use client';

import { useState, useEffect } from 'react';
import CreateDatasetModal from '../components/datasets/CreateDatasetModal';
import EditDatasetModal from '../components/datasets/EditDatasetModal';
import CreateTaskModal from '../components/tasks/CreateTaskModal';
import EditTaskModal from '../components/tasks/EditTaskModal';
import LoginModal from '../components/auth/LoginModal';
import SVOpsAPI from '@/lib/api';
import type { Task, Dataset, TaskStatus, UpdateTaskRequest, UpdateDatasetRequest } from '@/types/api';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('tasks');
  const [showCreateDatasetModal, setShowCreateDatasetModal] = useState(false);
  const [showEditDatasetModal, setShowEditDatasetModal] = useState(false);
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false);
  const [showEditTaskModal, setShowEditTaskModal] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [taskStatuses, setTaskStatuses] = useState<TaskStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [selectedTaskStatus, setSelectedTaskStatus] = useState<TaskStatus | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);

  // 인증 상태 확인
  useEffect(() => {
    checkAuthStatus();

    // 인증 에러 이벤트 리스너
    const handleAuthError = () => {
      setIsAuthenticated(false);
      setUser(null);
      setShowLoginModal(true);
    };

    window.addEventListener('auth-error', handleAuthError);
    return () => window.removeEventListener('auth-error', handleAuthError);
  }, []);

  // 인증된 경우에만 데이터 로드
  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const checkAuthStatus = () => {
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');

    if (token && savedUser) {
      setIsAuthenticated(true);
      setUser(JSON.parse(savedUser));
    } else {
      setShowLoginModal(true);
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [tasksResponse, datasetsResponse] = await Promise.all([
        SVOpsAPI.getTasks(),
        SVOpsAPI.getDatasets(),
      ]);
      setTasks(tasksResponse.items || []);
      setDatasets(datasetsResponse.items || []);

      // Task 로드 후 실행 중인 Task들의 상태 조회
      if (tasksResponse.items && tasksResponse.items.length > 0) {
        await loadTaskStatusesForTasks(tasksResponse.items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDataset = async (data: any) => {
    await SVOpsAPI.createDataset(data);
    setShowCreateDatasetModal(false);
    setError(null); // 성공시 에러 클리어
    await loadData(); // 목록 새로고침
  };

  const handleCreateTask = async (data: any) => {
    await SVOpsAPI.createTask(data);
    setShowCreateTaskModal(false);
    setError(null); // 성공시 에러 클리어
    await loadData(); // 목록 새로고침
  };

  const handleEditDataset = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setShowEditDatasetModal(true);
  };

  const handleUpdateDataset = async (data: UpdateDatasetRequest) => {
    if (!selectedDataset) return;
    await SVOpsAPI.updateDataset(selectedDataset.id, data);
    setShowEditDatasetModal(false);
    setSelectedDataset(null);
    setError(null);
    await loadData();
  };

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setShowEditTaskModal(true);
  };

  const handleUpdateTask = async (data: UpdateTaskRequest) => {
    if (!selectedTask) return;
    await SVOpsAPI.updateTask(selectedTask.id, data);
    setShowEditTaskModal(false);
    setSelectedTask(null);
    setError(null);
    await loadData();
  };

  const handleLoginSuccess = (token: string, userData: any) => {
    setIsAuthenticated(true);
    setUser(userData);
    setShowLoginModal(false);
    setError(null);

    // 헤더에 인증 상태 변경 알림
    window.dispatchEvent(new CustomEvent('auth-change'));
  };


  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('Are you sure you want to delete this task?')) {
      return;
    }

    try {
      await SVOpsAPI.deleteTask(taskId);
      await loadData(); // 목록 새로고침
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete task';
      setError(errorMessage);
    }
  };

  const handleDeleteDataset = async (datasetId: number) => {
    if (!confirm('Are you sure you want to delete this dataset?')) {
      return;
    }

    try {
      await SVOpsAPI.deleteDataset(datasetId);
      await loadData(); // 목록 새로고침
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete dataset';
      setError(errorMessage);
    }
  };

  const handleExecuteTask = async (taskId: number) => {
    try {
      await SVOpsAPI.executeTask(taskId, {});
      // Task 실행 후 전체 데이터 새로고침
      await loadData();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to execute task';
      setError(errorMessage);
    }
  };

  const loadTaskStatusesForTasks = async (tasks: Task[]) => {
    try {
      // 모든 Task의 상태를 가져오기 (pending/running/completed/failed 모두)
      const statusPromises = tasks.map(task => SVOpsAPI.getTaskStatus(task.id));
      const statuses = await Promise.all(statusPromises);
      setTaskStatuses(statuses);
    } catch (err) {
      console.error('Failed to load task statuses:', err);
      // 에러 발생시 빈 배열로 설정
      setTaskStatuses([]);
    }
  };

  const loadTaskStatuses = async () => {
    try {
      // 실행 중인 Task들의 상태만 가져오기
      const runningTasks = tasks.filter(task => task.status === 'running');
      const statusPromises = runningTasks.map(task => SVOpsAPI.getTaskStatus(task.id));
      const statuses = await Promise.all(statusPromises);
      setTaskStatuses(statuses);
    } catch (err) {
      console.error('Failed to load task statuses:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      pending: 'bg-gray-100 text-gray-800',
      running: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getExecutionStatusChip = (task: Task) => {
    const taskStatus = taskStatuses.find(ts => ts.task_id === task.id);

    if (!taskStatus) {
      // Task가 실행된 적 없으면 task.status 기준으로 표시
      const statusConfig = {
        pending: { bg: 'bg-gray-200', text: 'text-gray-600', label: 'Pending', animate: false },
        running: { bg: 'bg-yellow-200', text: 'text-yellow-800', label: 'Running', animate: true },
        completed: { bg: 'bg-green-200', text: 'text-green-800', label: 'Done', animate: false },
        failed: { bg: 'bg-red-200', text: 'text-red-800', label: 'Failed', animate: false },
      };
      const config = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.pending;

      return (
        <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full cursor-default ${config.bg
          } ${config.text} ${config.animate ? 'animate-pulse' : ''}`}>
          {config.label}
        </span>
      );
    }

    // TaskStatus가 있으면 execution 상태 표시
    const statusConfig = {
      pending: { bg: 'bg-gray-200', text: 'text-gray-600', label: 'Ready', animate: false },
      running: { bg: 'bg-yellow-200', text: 'text-yellow-800', label: 'Executing', animate: true },
      completed: { bg: 'bg-green-200', text: 'text-green-800', label: 'Complete', animate: false },
      failed: { bg: 'bg-red-200', text: 'text-red-800', label: 'Error', animate: false },
    };
    const config = statusConfig[taskStatus.overall_status] || statusConfig.pending;

    return (
      <button
        onClick={() => {
          setSelectedTaskStatus(taskStatus);
          setShowStatusModal(true);
        }}
        className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full cursor-pointer hover:opacity-80 transition-opacity ${config.bg
          } ${config.text} ${config.animate ? 'animate-pulse' : ''}`}
        title="Click to view execution details"
      >
        {config.label}
        {taskStatus.total_workflow_runs > 0 && (
          <span className="ml-1 text-xs opacity-75">({taskStatus.total_workflow_runs})</span>
        )}
      </button>
    );
  };

  return (
    <div className="space-y-6">

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-400">❌</div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Simple Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('tasks')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'tasks'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            Tasks
          </button>
          <button
            onClick={() => setActiveTab('datasets')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'datasets'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            Datasets
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'tasks' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900">Tasks</h2>
            <button
              onClick={() => setShowCreateTaskModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Create Task
            </button>
          </div>


          {/* Task Table */}
          <div className="bg-white rounded-lg border">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-medium text-gray-900">Task List</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Execution</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Branch</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commit</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Build Config</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Paths</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading ? (
                    <tr>
                      <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                        Loading tasks...
                      </td>
                    </tr>
                  ) : !tasks || tasks.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                        No tasks available. Create your first task to get started.
                      </td>
                    </tr>
                  ) : (
                    tasks.map((task) => {
                      return (
                        <tr key={task.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">{task.name}</div>
                            {task.description && (
                              <div className="text-sm text-gray-500">{task.description}</div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {task.customer}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getExecutionStatusChip(task)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {task.configuration.branch_name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900 font-mono">
                              {task.configuration.commit_id && task.configuration.commit_id.length > 8
                                ? task.configuration.commit_id.substring(0, 8) + '...'
                                : task.configuration.commit_id || 'HEAD'}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                              {task.configuration.build_config}
                              {task.configuration.build_config_customized && (
                                <span className="ml-1" title="Customized build config">⚙️</span>
                              )}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="space-y-1">
                              {/* Dataset Path */}
                              {task.dataset ? (
                                <div>
                                  <div className="text-xs font-medium text-gray-700"> {task.dataset.name}</div>
                                  <div className="text-xs text-gray-500 font-mono">{task.dataset.path}</div>
                                </div>
                              ) : (
                                <div className="text-xs text-gray-400"> Unknown dataset</div>
                              )}

                              {/* Video Output Path */}
                              <div>
                                {task.video_output.enabled ? (
                                  <>
                                    <div className="text-xs font-medium text-gray-700"> Video Output</div>
                                    <div className="text-xs text-gray-500 font-mono">{task.video_output.path || 'No path'}</div>
                                  </>
                                ) : (
                                  <div className="text-xs text-gray-400"> Disabled</div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <div className="flex flex-col items-center space-y-1">
                              <button
                                onClick={() => handleExecuteTask(task.id)}
                                className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition-colors w-full justify-center ${task.status === 'running'
                                  ? 'bg-yellow-100 text-yellow-800 cursor-not-allowed'
                                  : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                                  }`}
                                disabled={task.status === 'running'}
                              >
                                {task.status === 'running' ? (
                                  <>
                                    <svg className="w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Running...
                                  </>
                                ) : (
                                  <>
                                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6-4h8a2 2 0 012 2v8a2 2 0 01-2 2H8a2 2 0 01-2-2V8a2 2 0 012-2z" />
                                    </svg>
                                    Execute
                                  </>
                                )}
                              </button>
                              <button
                                onClick={() => handleEditTask(task)}
                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-indigo-100 text-indigo-800 hover:bg-indigo-200 transition-colors w-full justify-center"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteTask(task.id)}
                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-red-100 text-red-800 hover:bg-red-200 transition-colors w-full justify-center"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {activeTab === 'datasets' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900">Datasets</h2>
            <button
              onClick={() => setShowCreateDatasetModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Create Dataset
            </button>
          </div>

          {/* Dataset Table */}
          <div className="bg-white rounded-lg border">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-medium text-gray-900">Dataset List</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Path</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">GT Path</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                        Loading datasets...
                      </td>
                    </tr>
                  ) : !datasets || datasets.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                        No datasets available. Create your first dataset to get started.
                      </td>
                    </tr>
                  ) : (
                    datasets.map((dataset) => (
                      <tr key={dataset.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{dataset.name}</div>
                          {dataset.description && (
                            <div className="text-sm text-gray-500">{dataset.description}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                            {dataset.data_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                          {dataset.path}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                          {dataset.gt_path}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(dataset.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex flex-col items-center space-y-1">
                            <button
                              onClick={() => handleEditDataset(dataset)}
                              className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-indigo-100 text-indigo-800 hover:bg-indigo-200 transition-colors w-full justify-center"
                            >
                              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteDataset(dataset.id)}
                              className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-red-100 text-red-800 hover:bg-red-200 transition-colors w-full justify-center"
                            >
                              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <CreateDatasetModal
        isOpen={showCreateDatasetModal}
        onClose={() => setShowCreateDatasetModal(false)}
        onSubmit={handleCreateDataset}
      />

      <EditDatasetModal
        isOpen={showEditDatasetModal}
        onClose={() => {
          setShowEditDatasetModal(false);
          setSelectedDataset(null);
        }}
        onSubmit={handleUpdateDataset}
        dataset={selectedDataset}
      />

      <CreateTaskModal
        isOpen={showCreateTaskModal}
        onClose={() => setShowCreateTaskModal(false)}
        onSubmit={handleCreateTask}
        datasets={datasets}
      />

      <EditTaskModal
        isOpen={showEditTaskModal}
        onClose={() => {
          setShowEditTaskModal(false);
          setSelectedTask(null);
        }}
        onSubmit={handleUpdateTask}
        task={selectedTask}
        datasets={datasets}
      />

      <LoginModal
        isOpen={showLoginModal}
        onClose={() => { }} // 로그인 필수이므로 닫기 불가
        onSuccess={handleLoginSuccess}
      />

      {/* Task Status Detail Modal */}
      {selectedTaskStatus && (
        <div className={`fixed inset-0 z-50 ${showStatusModal ? '' : 'hidden'}`}>
          <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setShowStatusModal(false)} />
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <div className="px-6 py-4 border-b">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">
                    Task Execution Details: {selectedTaskStatus.task_name}
                  </h3>
                  <button
                    onClick={() => setShowStatusModal(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Overall Status */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Overall Status</h4>
                  <div className="flex items-center space-x-3">
                    <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${selectedTaskStatus.overall_status === 'completed' ? 'bg-green-100 text-green-800' :
                      selectedTaskStatus.overall_status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                        selectedTaskStatus.overall_status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                      }`}>
                      {selectedTaskStatus.overall_status}
                    </span>
                    <span className="text-sm text-gray-600">
                      Total Workflows: {selectedTaskStatus.total_workflow_runs}
                    </span>
                  </div>
                </div>

                {/* DAG Chain */}
                {selectedTaskStatus.dag_chain.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">DAG Chain</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedTaskStatus.dag_chain.map((dag, index) => (
                        <span key={index} className="inline-flex items-center px-3 py-1 text-sm font-medium bg-blue-100 text-blue-800 rounded-lg">
                          {dag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Workflow Runs */}
                {selectedTaskStatus.workflow_runs.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3">Workflow Runs</h4>
                    <div className="space-y-3">
                      {selectedTaskStatus.workflow_runs.map((run) => (
                        <div key={run.id} className="p-4 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <div className="font-medium text-sm text-gray-900">{run.workflow_id}</div>
                              <div className="text-xs text-gray-500">Run ID: {run.id}</div>
                            </div>
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${run.status === 'success' ? 'bg-green-100 text-green-800' :
                              run.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                                run.status === 'failed' ? 'bg-red-100 text-red-800' :
                                  'bg-gray-100 text-gray-800'
                              }`}>
                              {run.status}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
                            <div>
                              <span className="font-medium">Started:</span>{' '}
                              {run.start_date ? new Date(run.start_date).toLocaleString() : 'N/A'}
                            </div>
                            <div>
                              <span className="font-medium">Ended:</span>{' '}
                              {run.end_date ? new Date(run.end_date).toLocaleString() : 'N/A'}
                            </div>
                          </div>

                          {run.configuration.note && (
                            <div className="mt-2 text-xs text-gray-600">
                              <span className="font-medium">Note:</span> {run.configuration.note}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTaskStatus.workflow_runs.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-2xl mb-2">📋</div>
                    <p>No workflow runs found</p>
                    <p className="text-sm">This task hasn't been executed yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}