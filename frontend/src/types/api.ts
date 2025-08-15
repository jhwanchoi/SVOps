// API 응답 타입 정의
export interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface Dataset {
  id: number;
  name: string;
  description?: string;
  path: string;
  data_type: 'Surf';
  gt_path: string;
  created_by_id: number;
  created_at: string;
  updated_at?: string;
}

export interface Task {
  id: number;
  name: string;
  description?: string;
  customer: string;
  log_out_path: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at?: string;
  created_by_id: number;
  configuration: {
    branch_name: string;
    commit_id: string;
    build_config: string;
    build_config_customized: boolean;
    build_config_custom_conf: Record<string, any>;
    build_config_custom_ini: Record<string, any>;
  };
  dataset: {
    id: number;
    name: string;
    description?: string;
    path: string;
    data_type: 'Surf';
    gt_path: string;
    created_at: string;
    updated_at?: string;
    created_by_id: number;
  };
  video_output: {
    enabled: boolean;
    path: string;
  };
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: 'pending' | 'queued' | 'running' | 'success' | 'failed';
  start_date?: string;
  end_date?: string;
  configuration: {
    parameters: Record<string, any>;
    note?: string;
  };
}

export interface TaskStatus {
  task_id: number;
  task_status: 'pending' | 'running' | 'completed' | 'failed';
  task_name: string;
  dag_chain: string[];
  workflow_runs: WorkflowRun[];
  total_workflow_runs: number;
  overall_status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface ExecuteTaskResponse {
  task_id: number;
  total_dags: number;
  workflow_runs: WorkflowRun[];
  message: string;
}

// API 요청 타입
export interface CreateDatasetRequest {
  name: string;
  description?: string;
  path: string;
  data_type: 'Surf';
  gt_path: string;
}

export interface UpdateDatasetRequest {
  name?: string;
  description?: string;
  path?: string;
  data_type?: 'Surf';
  gt_path?: string;
}

export interface CreateTaskRequest {
  name: string;
  description?: string;
  customer: string;
  log_out_path: string;
  branch_name: string;
  commit_id: string;
  build_config: string;
  build_config_customized: boolean;
  build_config_custom_conf?: Record<string, any>;
  build_config_custom_ini?: Record<string, any>;
  dataset_id: number;
  video_out_enabled: boolean;
  video_out_path?: string;
}

export interface UpdateTaskRequest {
  name?: string;
  description?: string;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  customer?: string;
  log_out_path?: string;
  branch_name?: string;
  commit_id?: string;
  build_config?: string;
  build_config_customized?: boolean;
  build_config_custom_conf?: Record<string, any>;
  build_config_custom_ini?: Record<string, any>;
  dataset_id?: number;
  video_out_enabled?: boolean;
  video_out_path?: string;
}

export interface ExecuteTaskRequest {
  parameters?: Record<string, any>;
  note?: string;
}

// API 응답 래퍼
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}