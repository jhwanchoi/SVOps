'use client';

import { useState } from 'react';
import { Modal } from '../ui/modal';

interface CreateDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
}

type DatasetType = 'Surf';

export default function CreateDatasetModal({ isOpen, onClose, onSubmit }: CreateDatasetModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    data_type: 'Surf' as DatasetType,
    path: '',
    gt_path: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    // Basic validation
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Dataset name is required';
    }

    if (!formData.path.trim()) {
      newErrors.path = 'Dataset path is required';
    }

    if (!formData.gt_path.trim()) {
      newErrors.gt_path = 'Ground truth path is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setIsSubmitting(false);
      return;
    }

    try {
      // Prepare submission data
      const submissionData = {
        name: formData.name,
        description: formData.description || undefined,
        data_type: formData.data_type,
        path: formData.path,
        gt_path: formData.gt_path,
      };

      await onSubmit(submissionData);

      // Reset form
      setFormData({
        name: '',
        description: '',
        data_type: 'Surf',
        path: '',
        gt_path: '',
      });
      setErrors({});
      setSubmitError(null);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create dataset';
      setSubmitError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
    if (submitError) {
      setSubmitError(null);
    }
  };


  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Dataset" size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Message */}
        {submitError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <div className="flex">
              <div className="text-red-400">❌</div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{submitError}</div>
              </div>
            </div>
          </div>
        )}
        {/* Basic Information */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Basic Information</h4>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Dataset Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter dataset name"
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
              placeholder="Describe your dataset (optional)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Dataset Type
            </label>
            <div className="flex items-center p-4 border border-blue-600 bg-blue-50 rounded-lg">
              <div>
                <div className="font-medium text-gray-900">Surf</div>
                <div className="text-sm text-gray-600">Surface detection dataset</div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Dataset Path *
            </label>
            <input
              type="text"
              value={formData.path}
              onChange={(e) => handleInputChange('path', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="/path/to/dataset"
            />
            {errors.path && (
              <p className="text-red-500 text-xs mt-1">{errors.path}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ground Truth Path *
            </label>
            <input
              type="text"
              value={formData.gt_path}
              onChange={(e) => handleInputChange('gt_path', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="/path/to/ground/truth/data"
            />
            {errors.gt_path && (
              <p className="text-red-500 text-xs mt-1">{errors.gt_path}</p>
            )}
          </div>
        </div>


        {/* Submit buttons */}
        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Creating...' : 'Create Dataset'}
          </button>
        </div>
      </form>
    </Modal>
  );
}