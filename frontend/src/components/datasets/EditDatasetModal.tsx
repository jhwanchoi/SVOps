'use client';

import { useState, useEffect } from 'react';
import { Modal } from '../ui/modal';
import type { Dataset, UpdateDatasetRequest } from '@/types/api';

interface EditDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: UpdateDatasetRequest) => Promise<void>;
  dataset: Dataset | null;
}

export default function EditDatasetModal({
  isOpen,
  onClose,
  onSubmit,
  dataset,
}: EditDatasetModalProps) {
  const [formData, setFormData] = useState<UpdateDatasetRequest>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (dataset && isOpen) {
      setFormData({
        name: dataset.name,
        description: dataset.description || '',
        path: dataset.path,
        data_type: dataset.data_type,
        gt_path: dataset.gt_path,
      });
      setError(null);
    }
  }, [dataset, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dataset) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(formData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to update dataset');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof UpdateDatasetRequest, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (!dataset) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Edit Dataset: ${dataset.name}`} size="lg">
      <>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex">
                <div className="text-red-400">!</div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">{error}</div>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Dataset Information</h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dataset Name *
              </label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter dataset name"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter dataset description"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Type *
              </label>
              <select
                value={formData.data_type || ''}
                onChange={(e) => handleInputChange('data_type', e.target.value as 'Surf')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select data type...</option>
                <option value="Surf">Surf</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Path *
              </label>
              <input
                type="text"
                value={formData.path || ''}
                onChange={(e) => handleInputChange('path', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/path/to/dataset"
                required
              />
              <p className="mt-1 text-sm text-gray-500">
                Absolute path to the dataset directory
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ground Truth Path
              </label>
              <input
                type="text"
                value={formData.gt_path || ''}
                onChange={(e) => handleInputChange('gt_path', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/path/to/ground-truth (optional)"
              />
              <p className="mt-1 text-sm text-gray-500">
                Optional path to ground truth data for validation
              </p>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {isSubmitting ? 'Updating...' : 'Update Dataset'}
            </button>
          </div>
        </form>
      </>
    </Modal>
  );
}