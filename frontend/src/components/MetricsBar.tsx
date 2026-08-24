/**
 * TRIDENT MetricsBar Wrapper
 * Re-exports HUDMetricsBar for backward compatibility and spec alignment.
 */

import React from 'react';
import { HUDMetricsBar } from './HUDMetricsBar';
import type { ReconMetrics } from '../types/recon';

interface MetricsBarProps {
  metrics: ReconMetrics;
  nativeMatcher?: boolean;
  edgeInference?: boolean;
  merkleRoot?: string;
}

export const MetricsBar: React.FC<MetricsBarProps> = ({
  metrics,
  merkleRoot = '',
}) => {
  return <HUDMetricsBar metrics={metrics} merkleRoot={merkleRoot} />;
};
