'use client';

import { useState } from 'react';
import { Modal } from '../ui/modal';

import type { Dataset } from '@/types/api';

interface CreateTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
  datasets: Dataset[];
}

export default function CreateTaskModal({ isOpen, onClose, onSubmit, datasets }: CreateTaskModalProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    // Basic info
    name: '',
    description: '',
    customer: 'SURF',
    log_out_path: '',
    
    // Build configuration
    branch_name: 'develop',
    commit_id: 'HEAD',
    build_config: 'test-config-e2e',
    build_config_customized: false,
    build_config_custom_conf: '',
    build_config_custom_ini: '',
    
    // Inference configuration
    dataset_id: '',
    video_out_enabled: false,
    video_out_path: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const steps = [
    { id: 1, name: 'Basic Info', icon: '📋' },
    { id: 2, name: 'Build Config', icon: '🔧' },
    { id: 3, name: 'Inference Config', icon: '⚡' },
    { id: 4, name: 'Review', icon: '👁️' },
  ];

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear errors
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
    if (submitError) {
      setSubmitError(null);
    }
  };

  const validateStep = (step: number) => {
    const newErrors: Record<string, string> = {};

    switch (step) {
      case 1:
        if (!formData.name.trim()) {
          newErrors.name = 'Task name is required';
        }
        if (!formData.customer.trim()) {
          newErrors.customer = 'Customer is required';
        }
        if (!formData.log_out_path.trim()) {
          newErrors.log_out_path = 'Log output path is required';
        }
        break;
      case 2:
        if (!formData.branch_name.trim()) {
          newErrors.branch_name = 'Branch name is required';
        }
        if (!formData.commit_id.trim()) {
          newErrors.commit_id = 'Commit ID is required';
        }
        if (!formData.build_config.trim()) {
          newErrors.build_config = 'Build config is required';
        }
        if (formData.build_config_customized) {
          if (!formData.build_config_custom_conf.trim()) {
            newErrors.build_config_custom_conf = 'Custom config is required when customized is enabled';
          }
          if (!formData.build_config_custom_ini.trim()) {
            newErrors.build_config_custom_ini = 'Custom ini is required when customized is enabled';
          }
        }
        break;
      case 3:
        if (!formData.dataset_id) {
          newErrors.dataset_id = 'Dataset selection is required';
        }
        if (formData.video_out_enabled && !formData.video_out_path.trim()) {
          newErrors.video_out_path = 'Video output path is required when video output is enabled';
        }
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 4));
    }
  };

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(currentStep)) return;
    
    setIsSubmitting(true);
    setSubmitError(null);
    
    try {
      // 데이터 변환
      const submissionData = {
        ...formData,
        dataset_id: parseInt(formData.dataset_id),
        build_config_custom_conf: formData.build_config_customized && formData.build_config_custom_conf 
          ? JSON.parse(formData.build_config_custom_conf) 
          : {},
        build_config_custom_ini: formData.build_config_customized && formData.build_config_custom_ini 
          ? JSON.parse(formData.build_config_custom_ini) 
          : {},
        video_out_path: formData.video_out_enabled ? formData.video_out_path : '',
      };

      await onSubmit(submissionData);
      
      // Reset form
      setFormData({
        name: '',
        description: '',
        customer: 'SURF',
        log_out_path: '',
        branch_name: 'develop',
        commit_id: 'HEAD',
        build_config: 'test-config-e2e',
        build_config_customized: false,
        build_config_custom_conf: '',
        build_config_custom_ini: '',
        dataset_id: '',
        video_out_enabled: false,
        video_out_path: '',
      });
      setCurrentStep(1);
      setErrors({});
      setSubmitError(null);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create task';
      setSubmitError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Basic Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Task Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter task name"
              />
              {errors.name && (
                <p className="text-red-500 text-xs mt-1">{errors.name}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Describe your task (optional)"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Customer *
              </label>
              <input
                type="text"
                value={formData.customer}
                onChange={(e) => handleInputChange('customer', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Customer name"
              />
              {errors.customer && (
                <p className="text-red-500 text-xs mt-1">{errors.customer}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Log Output Path *
              </label>
              <input
                type="text"
                value={formData.log_out_path}
                onChange={(e) => handleInputChange('log_out_path', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/path/to/log/output"
              />
              {errors.log_out_path && (
                <p className="text-red-500 text-xs mt-1">{errors.log_out_path}</p>
              )}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 mb-4">
              <span className="text-2xl">🔧</span>
              <h3 className="text-lg font-medium text-gray-900">Build Configuration</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Branch Name *
                </label>
                <input
                  type="text"
                  value={formData.branch_name}
                  onChange={(e) => handleInputChange('branch_name', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="main, develop, feature/branch-name"
                />
                {errors.branch_name && (
                  <p className="text-red-500 text-xs mt-1">{errors.branch_name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Commit ID *
                </label>
                <input
                  type="text"
                  value={formData.commit_id}
                  onChange={(e) => handleInputChange('commit_id', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., a1b2c3d4e5f6"
                />
                {errors.commit_id && (
                  <p className="text-red-500 text-xs mt-1">{errors.commit_id}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Build Config *
              </label>
              <input
                type="text"
                value={formData.build_config}
                onChange={(e) => handleInputChange('build_config', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., test-config-e2e, debug, release"
              />
              {errors.build_config && (
                <p className="text-red-500 text-xs mt-1">{errors.build_config}</p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.build_config_customized}
                  onChange={(e) => handleInputChange('build_config_customized', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">Enable Custom Build Configuration</span>
              </label>
            </div>

            {formData.build_config_customized && (
              <div className="space-y-4 mt-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Custom Config (JSON) *
                  </label>
                  <textarea
                    value={formData.build_config_custom_conf}
                    onChange={(e) => handleInputChange('build_config_custom_conf', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    rows={10}
                    placeholder='{\n  "optimization_level": "O3",\n  "target_arch": "x86_64",\n  "flags": ["-Wall", "-Werror"]\n}'
                  />
                  {errors.build_config_custom_conf && (
                    <p className="text-red-500 text-xs mt-1">{errors.build_config_custom_conf}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Custom INI Configuration *
                  </label>
                  <textarea
                    value={formData.build_config_custom_ini}
                    onChange={(e) => handleInputChange('build_config_custom_ini', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    rows={10}
                    placeholder='{\n  "section1": {\n    "key1": "value1",\n    "key2": "value2"\n  },\n  "section2": {\n    "key3": "value3"\n  }\n}'
                  />
                  {errors.build_config_custom_ini && (
                    <p className="text-red-500 text-xs mt-1">{errors.build_config_custom_ini}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 mb-4">
              <span className="text-2xl">⚡</span>
              <h3 className="text-lg font-medium text-gray-900">Inference Configuration</h3>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dataset *
              </label>
              <select
                value={formData.dataset_id}
                onChange={(e) => handleInputChange('dataset_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a dataset</option>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name} ({dataset.data_type})
                  </option>
                ))}
              </select>
              {errors.dataset_id && (
                <p className="text-red-500 text-xs mt-1">{errors.dataset_id}</p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.video_out_enabled}
                  onChange={(e) => handleInputChange('video_out_enabled', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">Enable Video Output</span>
              </label>
            </div>

            {formData.video_out_enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Video Output Path *
                </label>
                <input
                  type="text"
                  value={formData.video_out_path}
                  onChange={(e) => handleInputChange('video_out_path', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="/path/to/video/output"
                />
                {errors.video_out_path && (
                  <p className="text-red-500 text-xs mt-1">{errors.video_out_path}</p>
                )}
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <h3 className="text-lg font-medium text-gray-900">Review & Submit</h3>
            
            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <div>
                <h4 className="font-medium text-gray-900">Basic Information</h4>
                <div className="mt-2 text-sm text-gray-600">
                  <p><strong>Name:</strong> {formData.name}</p>
                  {formData.description && <p><strong>Description:</strong> {formData.description}</p>}
                  <p><strong>Customer:</strong> {formData.customer}</p>
                  <p><strong>Log Output Path:</strong> {formData.log_out_path}</p>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900">Build Configuration</h4>
                <div className="mt-2 text-sm text-gray-600">
                  <p><strong>Branch:</strong> {formData.branch_name}</p>
                  <p><strong>Commit ID:</strong> {formData.commit_id}</p>
                  <p><strong>Build Config:</strong> {formData.build_config}</p>
                  <p><strong>Customized:</strong> {formData.build_config_customized ? 'Yes' : 'No'}</p>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900">Inference Configuration</h4>
                <div className="mt-2 text-sm text-gray-600">
                  <p><strong>Dataset:</strong> {datasets.find(d => d.id.toString() === formData.dataset_id)?.name || 'None'}</p>
                  <p><strong>Video Output:</strong> {formData.video_out_enabled ? 'Enabled' : 'Disabled'}</p>
                  {formData.video_out_enabled && (
                    <p><strong>Video Output Path:</strong> {formData.video_out_path}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Task" size="xl">
      <div className="flex flex-col h-[600px]">
        {/* Error Message */}
        {submitError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
            <div className="flex">
              <div className="text-red-400">❌</div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{submitError}</div>
              </div>
            </div>
          </div>
        )}
        
        {/* Steps indicator */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                  currentStep >= step.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {currentStep > step.id ? '✓' : step.icon}
              </div>
              <span className={`ml-2 text-sm ${
                currentStep >= step.id ? 'text-blue-600 font-medium' : 'text-gray-500'
              }`}>
                {step.name}
              </span>
              {index < steps.length - 1 && (
                <div className={`ml-4 w-8 h-0.5 ${
                  currentStep > step.id ? 'bg-blue-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto">
          {renderStepContent()}
        </div>

        {/* Navigation buttons */}
        <div className="flex justify-between pt-6 border-t border-gray-200">
          <div>
            {currentStep > 1 && (
              <button
                onClick={handlePrevious}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Previous
              </button>
            )}
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            
            {currentStep < 4 ? (
              <button
                onClick={handleNext}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Creating...' : 'Create Task'}
              </button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}