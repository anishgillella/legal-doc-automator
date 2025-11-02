'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export function ThreeDBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfafafa);

    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);

    // Create floating cubes
    const cubes: THREE.Mesh[] = [];
    const cubeGeometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
    
    for (let i = 0; i < 12; i++) {
      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color().setHSL(0.6, 0.7, 0.5 + Math.random() * 0.3), // Primary color variations
        wireframe: false,
        emissive: new THREE.Color().setHSL(0.6, 0.7, 0.3),
      });

      const cube = new THREE.Mesh(cubeGeometry, material);
      cube.position.set(
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 8
      );
      cube.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        Math.random() * Math.PI
      );

      scene.add(cube);
      cubes.push(cube);
    }

    // Add lighting
    const light1 = new THREE.PointLight(0x5b7bff, 1, 100);
    light1.position.set(5, 5, 5);
    scene.add(light1);

    const light2 = new THREE.PointLight(0xff7b5b, 0.5, 100);
    light2.position.set(-5, -5, 5);
    scene.add(light2);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    // Animation loop
    let animationId: number;
    const animate = () => {
      animationId = requestAnimationFrame(animate);

      // Rotate and move cubes
      cubes.forEach((cube, index) => {
        cube.rotation.x += 0.003 + index * 0.0002;
        cube.rotation.y += 0.004 + index * 0.0003;
        
        // Gentle floating motion
        cube.position.y += Math.sin(Date.now() * 0.0001 + index) * 0.001;
        cube.position.x += Math.cos(Date.now() * 0.00008 + index) * 0.001;
      });

      renderer.render(scene, camera);
    };

    animate();

    // Handle resize
    const handleResize = () => {
      if (!containerRef.current) return;
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
      containerRef.current?.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-0"
      style={{ opacity: 0.4 }}
    />
  );
}
