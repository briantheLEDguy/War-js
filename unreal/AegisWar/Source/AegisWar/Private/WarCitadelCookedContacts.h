#pragma once
#include "CoreMinimal.h"
class FJsonObject;
struct FBodyInstance;
struct FOverlapResult;

/** Read-only live geometry for diagnostics and route-only typed placement checks. */
namespace WarCitadelCookedContacts
{
    enum class EContactDecision : uint8 { RawClear,Separated,Blocked,Unresolved };
    struct FBodyContact
    {
        EContactDecision Decision=EContactDecision::Unresolved;
        bool ReadLockEntered=false,Complete=false,MtdBlocking=true,StaticPolicySupported=false;
        int32 SelectedShapes=0;
    };
    struct FSceneContact
    {
        EContactDecision Decision=EContactDecision::Unresolved;
        int32 RawBlockingHits=0,UniqueBodies=0,SeparatedBodies=0,BlockedBodies=0,UnresolvedBodies=0;
        TSharedPtr<FJsonObject> Diagnostic;
    };
    struct FTriangleSeparation
    {
        bool Certified=false;
        double SeparatingPlaneGapCm=0,NumericalGuardCm=0;
        bool ProjectionAxisRecorded=false;
        FVector ProjectionOrigin=FVector::ZeroVector,SeparatingAxis=FVector::ZeroVector;
        double AxisLengthSquared=0,CapsuleMinimum=0,CapsuleMaximum=0,TriangleMinimum=0,TriangleMaximum=0;
        double GapTriangleAfterCapsule=0,GapCapsuleAfterTriangle=0;
    };
    FTriangleSeparation TriangleSeparation(const FVector& AxisStart,const FVector& AxisEnd,
        double Radius,const FVector& A,const FVector& B,const FVector& C);
    bool ConservativeLocalBounds(const FMatrix& LocalToWorld,const FBox& WorldBounds,
        FBox& LocalBounds,double& MaximumRoundtripError);
    TSharedPtr<FJsonObject> Witness(const FBodyInstance* Body,const FVector& Center,
        const FQuat& Rotation,double Radius,double HalfHeight,bool TraceComplex,FBodyContact* Contact=nullptr);
    /** Diagnostic all-hit aggregation from fresh native bodies; saved JSON is never an input. */
    FSceneContact ResolveOverlaps(const TArray<FOverlapResult>& Hits,const FVector& Center,
        const FQuat& Rotation,double Radius,double HalfHeight,bool TraceComplex);
}
