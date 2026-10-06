#include "WarCitadelCookedContacts.h"
#include "Dom/JsonObject.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/PhysicsFiltering.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Chaos/ImplicitObjectScaled.h"
#include "Chaos/ImplicitObjectTransformed.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include <cfloat>

namespace
{
    TArray<TSharedPtr<FJsonValue>> Vector(const FVector& Value)
    {
        return {MakeShared<FJsonValueNumber>(Value.X),MakeShared<FJsonValueNumber>(Value.Y),MakeShared<FJsonValueNumber>(Value.Z)};
    }
    bool Triangles(const Chaos::FImplicitObject& Geometry,const FMatrix& Parent,const FBox& WorldBounds,
        const FVector& AxisStart,const FVector& AxisEnd,double Radius,const TSharedRef<FJsonObject>& Row,
        bool& FullCapsuleSeparated,int32 Depth=0)
    {
        FullCapsuleSeparated=false;
        if (Depth>8) return false;
        if (const auto* Transformed=Geometry.GetObject<Chaos::FImplicitObjectTransformed>())
        {
            Row->SetStringField(TEXT("transformedWrapper"),Transformed->GetTransform().ToString());
            return Triangles(*Transformed->GetTransformedObject(),Transformed->GetTransform().ToMatrixWithScale()*Parent,WorldBounds,
                AxisStart,AxisEnd,Radius,Row,FullCapsuleSeparated,Depth+1);
        }
        Chaos::FVec3 Scale;Chaos::FReal Margin=0;
        const auto* Mesh=Chaos::UnwrapImplicit<Chaos::FTriangleMeshImplicitObject>(Geometry,Scale,Margin);
        if (!Mesh || Scale.ContainsNaN() || Scale.GetAbsMin()<SMALL_NUMBER) return false;
        // Keep the exact affine composition: rotated nonuniform wrappers can
        // introduce shear, which cannot be represented by an FTransform.
        const FMatrix Frame=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(Scale)).ToMatrixWithScale()*Parent;
        FBox Local;double RoundtripError=0;
        const bool Verified=WarCitadelCookedContacts::ConservativeLocalBounds(Frame,WorldBounds,Local,RoundtripError);
        Row->SetBoolField(TEXT("affineQueryBoundsVerified"),Verified);
        Row->SetNumberField(TEXT("maximumBoundsRoundtripErrorCm"),RoundtripError);
        if (!Verified) return false;
        // Diagnostic candidate collection must round outward when Chaos converts
        // this AABB to float. This expands only the broadphase search box.
        const double Padding=FMath::Max(1.e-6,32.*FLT_EPSILON*(FMath::Max(Local.Min.GetAbsMax(),Local.Max.GetAbsMax())+1.));
        Local=Local.ExpandBy(Padding);Row->SetNumberField(TEXT("diagnosticBroadphasePaddingCm"),Padding);
        const FVector X(Frame.M[0][0],Frame.M[0][1],Frame.M[0][2]);
        const FVector Y(Frame.M[1][0],Frame.M[1][1],Frame.M[1][2]);
        const FVector Z(Frame.M[2][0],Frame.M[2][1],Frame.M[2][2]);
        const bool RigidUnit=FMath::Abs(X.SizeSquared()-1)<=1.e-10 && FMath::Abs(Y.SizeSquared()-1)<=1.e-10
            && FMath::Abs(Z.SizeSquared()-1)<=1.e-10 && FMath::Abs(FVector::DotProduct(X,Y))<=1.e-10
            && FMath::Abs(FVector::DotProduct(X,Z))<=1.e-10 && FMath::Abs(FVector::DotProduct(Y,Z))<=1.e-10
            && FMath::Abs(Frame.Determinant()-1)<=1.e-10;
        Row->SetBoolField(TEXT("rigidUnitSeparationPolicySupported"),RigidUnit);
        Row->SetArrayField(TEXT("wrapperScale"),Vector(FVector(Scale)));Row->SetNumberField(TEXT("collisionMarginCm"),Margin);
        TArray<TSharedPtr<FJsonValue>> MatrixRows;
        for (int32 I=0;I<4;++I)
        {
            TArray<TSharedPtr<FJsonValue>> Values;
            for (int32 J=0;J<4;++J) Values.Add(MakeShared<FJsonValueNumber>(Frame.M[I][J]));
            MatrixRows.Add(MakeShared<FJsonValueArray>(Values));
        }
        Row->SetArrayField(TEXT("triangleLocalToWorldMatrix"),MatrixRows);
        Row->SetBoolField(TEXT("cullsBackFaceRaycast"),Mesh->GetCullsBackFaceRaycast());
        Row->SetNumberField(TEXT("liveCookedTriangleCount"),Mesh->Elements().GetNumTriangles());
        Row->SetArrayField(TEXT("localQueryMinimum"),Vector(Local.Min));Row->SetArrayField(TEXT("localQueryMaximum"),Vector(Local.Max));
        TArray<int32> Indices;Mesh->FindOverlappingTriangles(Chaos::FAABB3(Chaos::FVec3(Local.Min),Chaos::FVec3(Local.Max)),Indices);
        Indices.Sort();Row->SetNumberField(TEXT("candidateTriangleCount"),Indices.Num());
        constexpr int32 Limit=4096;Row->SetNumberField(TEXT("triangleLimit"),Limit);Row->SetBoolField(TEXT("truncated"),Indices.Num()>Limit);
        TArray<TSharedPtr<FJsonValue>> Rows;bool Finite=true,Separated=RigidUnit && Margin==0 && Indices.Num()>0 && Indices.Num()<=Limit;
        double MinimumGap=DBL_MAX,MaximumGuard=0;
        for (int32 I=0;I<FMath::Min(Indices.Num(),Limit);++I)
        {
            Chaos::FTriangle Triangle;int32 A,B,C;
            Mesh->GetTransformedTriangle(Indices[I],Chaos::FRigidTransform3::Identity,Triangle,A,B,C);
            auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("internalTriangle"),Indices[I]);
            Item->SetNumberField(TEXT("externalFace"),Mesh->GetExternalFaceIndexFromInternal(Indices[I]));
            Item->SetArrayField(TEXT("cookedVertexIndices"),{MakeShared<FJsonValueNumber>(A),MakeShared<FJsonValueNumber>(B),MakeShared<FJsonValueNumber>(C)});
            TArray<TSharedPtr<FJsonValue>> Vertices;FVector Points[3];bool Valid=true;
            for (int32 J=0;J<3;++J)
            {
                Points[J]=FVector(Frame.TransformPosition(FVector(Triangle[J])));Valid&=!Points[J].ContainsNaN();
                if (Points[J].ContainsNaN()) Vertices.Add(MakeShared<FJsonValueNull>());
                else Vertices.Add(MakeShared<FJsonValueArray>(Vector(Points[J])));
            }
            Finite&=Valid;Item->SetBoolField(TEXT("finite"),Valid);Item->SetArrayField(TEXT("worldVertices"),Vertices);
            if (Valid)
            {
                const auto Certificate=WarCitadelCookedContacts::TriangleSeparation(AxisStart,AxisEnd,Radius,Points[0],Points[1],Points[2]);
                Item->SetBoolField(TEXT("fullCapsuleSeparationCertified"),Certificate.Certified);
                Item->SetNumberField(TEXT("separatingPlaneGapCm"),Certificate.SeparatingPlaneGapCm);
                Item->SetNumberField(TEXT("numericalGuardCm"),Certificate.NumericalGuardCm);
                Item->SetNumberField(TEXT("certificateVersion"),1);
                Item->SetNumberField(TEXT("guardPolicyVersion"),1);
                Item->SetBoolField(TEXT("projectionAxisRecorded"),Certificate.ProjectionAxisRecorded);
                if (Certificate.ProjectionAxisRecorded)
                {
                    Item->SetArrayField(TEXT("projectionOriginCm"),Vector(Certificate.ProjectionOrigin));
                    Item->SetArrayField(TEXT("separatingUnitAxis"),Vector(Certificate.SeparatingAxis));
                    Item->SetNumberField(TEXT("separatingAxisSquaredLength"),Certificate.AxisLengthSquared);
                    Item->SetArrayField(TEXT("capsuleProjectionCm"),{MakeShared<FJsonValueNumber>(Certificate.CapsuleMinimum),
                        MakeShared<FJsonValueNumber>(Certificate.CapsuleMaximum)});
                    Item->SetArrayField(TEXT("triangleProjectionCm"),{MakeShared<FJsonValueNumber>(Certificate.TriangleMinimum),
                        MakeShared<FJsonValueNumber>(Certificate.TriangleMaximum)});
                    Item->SetNumberField(TEXT("gapTriangleAfterCapsuleCm"),Certificate.GapTriangleAfterCapsule);
                    Item->SetNumberField(TEXT("gapCapsuleAfterTriangleCm"),Certificate.GapCapsuleAfterTriangle);
                    Item->SetStringField(TEXT("projectionGapDirection"),Certificate.GapTriangleAfterCapsule>=Certificate.GapCapsuleAfterTriangle
                        ? TEXT("triangle_above_capsule") : TEXT("capsule_above_triangle"));
                }
                Separated&=Certificate.Certified;MinimumGap=FMath::Min(MinimumGap,Certificate.SeparatingPlaneGapCm);
                MaximumGuard=FMath::Max(MaximumGuard,Certificate.NumericalGuardCm);
                const FVector Cross=FVector::CrossProduct(Points[1]-Points[0],Points[2]-Points[0]);
                Item->SetNumberField(TEXT("areaCm2"),Cross.Size()*.5);
                Item->SetArrayField(TEXT("worldCross"),Vector(Cross));
                Item->SetArrayField(TEXT("edgeLengthsCm"),{MakeShared<FJsonValueNumber>(FVector::Distance(Points[0],Points[1])),
                    MakeShared<FJsonValueNumber>(FVector::Distance(Points[1],Points[2])),MakeShared<FJsonValueNumber>(FVector::Distance(Points[2],Points[0]))});
            }
            Rows.Add(MakeShared<FJsonValueObject>(Item));
        }
        Row->SetArrayField(TEXT("triangles"),Rows);Row->SetBoolField(TEXT("finiteTriangles"),Finite);
        Row->SetBoolField(TEXT("separatedFullCapsuleDiagnostic"),Separated && Finite);
        Row->SetNumberField(TEXT("minimumCandidateSeparatingPlaneGapCm"),MinimumGap==DBL_MAX?0:MinimumGap);
        Row->SetNumberField(TEXT("maximumNumericalGuardCm"),MaximumGuard);
        FullCapsuleSeparated=Separated && Finite;
        return Finite && Indices.Num()<=Limit;
    }
}

WarCitadelCookedContacts::FTriangleSeparation WarCitadelCookedContacts::TriangleSeparation(
    const FVector& Start,const FVector& End,double Radius,const FVector& A,const FVector& B,const FVector& C)
{
    FTriangleSeparation Result;
    const FVector Points[]={Start,End,A,B,C};double Magnitude=Radius;
    if (!FMath::IsFinite(Radius) || Radius<=0 || Radius>1.e6) return Result;
    for (const FVector& P:Points)
    {
        if (P.ContainsNaN() || P.GetAbsMax()>1.e6) return Result;
        Magnitude=FMath::Max(Magnitude,P.GetAbsMax());
    }
    const FVector Normal=FVector::CrossProduct(B-A,C-A);
    const double LongestSquared=FMath::Max3((B-A).SizeSquared(),(C-B).SizeSquared(),(A-C).SizeSquared());
    if (!FMath::IsFinite(LongestSquared) || LongestSquared<=1.e-12
        || Normal.Size()<=LongestSquared*1.e-6) return Result;
    // Reject ambiguous separation with a conservative numerical guard. This is
    // an engineering guard, not a proved bound on every Chaos arithmetic path.
    Result.NumericalGuardCm=FMath::Max(.001,32.*FLT_EPSILON*(Magnitude+FMath::Sqrt(LongestSquared)+Radius+(End-Start).Size()));
    const FVector Origin=(Start+End)*.5;
    const auto TryAxis=[&](const FVector& Candidate)
    {
        if (Candidate.ContainsNaN() || Candidate.SizeSquared()<=1.e-20) return;
        const FVector N=Candidate.GetSafeNormal(1.e-20);
        const double NormSquared=N.SizeSquared();
        if (!FMath::IsFinite(NormSquared) || FMath::Abs(NormSquared-1)>1.e-10) return;
        const double Support=Radius*FMath::Sqrt(NormSquared);
        const double LowCapsule=FMath::Min(FVector::DotProduct(Start-Origin,N),FVector::DotProduct(End-Origin,N))-Support;
        const double HighCapsule=FMath::Max(FVector::DotProduct(Start-Origin,N),FVector::DotProduct(End-Origin,N))+Support;
        const double LowTriangle=FMath::Min3(FVector::DotProduct(A-Origin,N),FVector::DotProduct(B-Origin,N),FVector::DotProduct(C-Origin,N));
        const double HighTriangle=FMath::Max3(FVector::DotProduct(A-Origin,N),FVector::DotProduct(B-Origin,N),FVector::DotProduct(C-Origin,N));
        const double Gap=FMath::Max(LowTriangle-HighCapsule,LowCapsule-HighTriangle);
        if (FMath::IsFinite(Gap) && (!Result.ProjectionAxisRecorded || Gap>Result.SeparatingPlaneGapCm))
        {
            Result.ProjectionAxisRecorded=true;Result.ProjectionOrigin=Origin;Result.SeparatingAxis=N;
            Result.AxisLengthSquared=NormSquared;Result.CapsuleMinimum=LowCapsule;Result.CapsuleMaximum=HighCapsule;
            Result.TriangleMinimum=LowTriangle;Result.TriangleMaximum=HighTriangle;
            Result.GapTriangleAfterCapsule=LowTriangle-HighCapsule;Result.GapCapsuleAfterTriangle=LowCapsule-HighTriangle;
            Result.SeparatingPlaneGapCm=Gap;
        }
    };
    // Candidate closest-point calculations only suggest axes. The interval
    // certificate tests the entire triangle and the full capsule on each axis,
    // so an inaccurate closest-point candidate cannot certify an intersection.
    TryAxis(Normal);
    for (const FVector& P:{Start,End}) TryAxis(FMath::ClosestPointOnTriangleToPoint(P,A,B,C)-P);
    const FVector Vertices[]={A,B,C};
    for (int32 I=0;I<3;++I)
    {
        const FVector P=Vertices[I],Q=Vertices[(I+1)%3];FVector CapsulePoint,EdgePoint;
        FMath::SegmentDistToSegmentSafe(Start,End,P,Q,CapsulePoint,EdgePoint);
        TryAxis(EdgePoint-CapsulePoint);
        TryAxis(P-FMath::ClosestPointOnSegment(P,Start,End));
    }
    Result.Certified=Result.ProjectionAxisRecorded && Result.SeparatingPlaneGapCm>Result.NumericalGuardCm;
    return Result;
}

bool WarCitadelCookedContacts::ConservativeLocalBounds(const FMatrix& Frame,const FBox& WorldBounds,
    FBox& LocalBounds,double& MaximumRoundtripError)
{
    LocalBounds=FBox(ForceInit);MaximumRoundtripError=0;
    if (!WorldBounds.IsValid || WorldBounds.Min.ContainsNaN() || WorldBounds.Max.ContainsNaN()
        || Frame.ContainsNaN() || !FMath::IsFinite(Frame.Determinant())
        || FMath::Abs(Frame.Determinant())<=UE_DOUBLE_SMALL_NUMBER) return false;
    const FMatrix Inverse=Frame.Inverse();
    if (Inverse.ContainsNaN()) return false;
    for (int32 I=0;I<8;++I)
    {
        const FVector World((I&1)?WorldBounds.Max.X:WorldBounds.Min.X,
            (I&2)?WorldBounds.Max.Y:WorldBounds.Min.Y,(I&4)?WorldBounds.Max.Z:WorldBounds.Min.Z);
        const FVector Local(Inverse.TransformPosition(World));
        const FVector Restored(Frame.TransformPosition(Local));
        if (Local.ContainsNaN() || Restored.ContainsNaN()) return false;
        MaximumRoundtripError=FMath::Max(MaximumRoundtripError,FVector::Distance(World,Restored));
        LocalBounds+=Local;
    }
    return LocalBounds.IsValid && MaximumRoundtripError<=1.e-6;
}

TSharedPtr<FJsonObject> WarCitadelCookedContacts::Witness(const FBodyInstance* Body,const FVector& Center,
    const FQuat& Rotation,double Radius,double HalfHeight,bool TraceComplex,FBodyContact* Contact)
{
    if (Contact) *Contact=FBodyContact();
    auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("diagnosticOnly"),true);
    Result->SetNumberField(TEXT("schemaVersion"),2);
    Result->SetBoolField(TEXT("complete"),false);Result->SetStringField(TEXT("source"),TEXT("live_physics_shape_geometry_under_execute_read"));
    if (!Body || !Body->IsValidBodyInstance() || Center.ContainsNaN() || Rotation.ContainsNaN() || !FMath::IsFinite(Radius)
        || !FMath::IsFinite(HalfHeight) || Radius<=0 || HalfHeight<Radius || !Rotation.IsNormalized()) return Result;
    const FVector Axis=Rotation.RotateVector(FVector::UpVector)*(HalfHeight-Radius);
    const FVector Extent=Axis.GetAbs()+FVector(Radius);
    const FBox Bounds(Center-Extent,Center+Extent);
    Result->SetArrayField(TEXT("capsuleAxisStart"),Vector(Center-Axis));Result->SetArrayField(TEXT("capsuleAxisEnd"),Vector(Center+Axis));
    Result->SetNumberField(TEXT("capsuleRadiusCm"),Radius);Result->SetArrayField(TEXT("worldBoundsMinimum"),Vector(Bounds.Min));
    Result->SetArrayField(TEXT("worldBoundsMaximum"),Vector(Bounds.Max));
    const FBodyInstance* Target=Body->WeldParent ? Body->WeldParent : Body;
    Result->SetStringField(TEXT("targetBody"),Target->GetBodyDebugName());Result->SetBoolField(TEXT("welded"),Target!=Body);
    bool Locked=false,Complete=true,Separated=true,MtdBlocking=true,StaticPolicy=false;int32 Eligible=0;TArray<TSharedPtr<FJsonValue>> Rows;
    FPhysicsCommand::ExecuteRead(Target->GetPhysicsActor(),[&](const FPhysicsActorHandle& Actor)
    {
        Locked=true;const FTransform ActorFrame=FPhysicsInterface::GetGlobalPose_AssumesLocked(Actor);
        const auto* Owner=Body->OwnerComponent.Get();
        StaticPolicy=Body==Target && Body->InstanceBodyIndex==INDEX_NONE && Owner && Owner->Mobility==EComponentMobility::Static
            && Owner->GetComponentScale().Equals(FVector::OneVector,1.e-10)
            && !Owner->IsSimulatingPhysics() && FPhysicsInterface::IsStatic(Actor);
        FMTDResult Mtd{};
        MtdBlocking=Body->OverlapTest_AssumesLocked(Center,Rotation,FCollisionShape::MakeCapsule(Radius,HalfHeight),&Mtd,TraceComplex);
        Result->SetBoolField(TEXT("sameReadLockMtdBlocking"),MtdBlocking);
        Result->SetBoolField(TEXT("staticSingleBodyPolicySupported"),StaticPolicy);
        Result->SetNumberField(TEXT("sameReadLockMtdDistanceCm"),FMath::IsFinite(Mtd.Distance)?Mtd.Distance:0);
        Result->SetStringField(TEXT("actorWorldTransform"),ActorFrame.ToString());
        PhysicsInterfaceTypes::FInlineShapeArray Shapes;FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes);
        Result->SetNumberField(TEXT("liveShapeCount"),Shapes.Num());
        for (int32 I=0;I<Shapes.Num();++I)
        {
            auto Row=MakeShared<FJsonObject>();const auto& Shape=Shapes[I];
            const auto Flags=FPhysicsInterface::GetShapeFilterData(Shape);
            const bool Simple=Flags.HasFlag(Chaos::EFilterFlags::SimpleCollision),Complex=Flags.HasFlag(Chaos::EFilterFlags::ComplexCollision);
            const bool Bound=Target->IsShapeBoundToBody(Shape),Query=FPhysicsInterface::IsQueryShape(Shape);
            const bool Selected=Bound && Query && (TraceComplex ? Complex : Simple);
            // A welded root can have no WeldParent of its own. Reject its
            // foreign selected-query shapes rather than overlooking child geometry.
            if (Query && (TraceComplex ? Complex : Simple) && !Bound) StaticPolicy=false;
            Row->SetNumberField(TEXT("shapeIndex"),I);Row->SetBoolField(TEXT("boundToQueriedBody"),Bound);
            Row->SetBoolField(TEXT("queryShape"),Query);Row->SetBoolField(TEXT("simpleCollision"),Simple);Row->SetBoolField(TEXT("complexCollision"),Complex);
            Row->SetBoolField(TEXT("selected"),Selected);
            if (Selected)
            {
                ++Eligible;const auto Collection=FPhysicsInterface::GetGeometryCollection(Shape);const auto& Geometry=Collection.GetGeometry();
                Row->SetNumberField(TEXT("liveGeometryType"),int32(Geometry.GetType()));
                bool ShapeSeparated=false;
                const bool Covered=Triangles(Geometry,ActorFrame.ToMatrixWithScale(),Bounds,Center-Axis,Center+Axis,Radius,Row,ShapeSeparated);Complete&=Covered;
                Separated&=Covered && ShapeSeparated;
                Row->SetBoolField(TEXT("triangleWitnessComplete"),Covered);
            }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    });
    Result->SetBoolField(TEXT("readLockEntered"),Locked);Result->SetNumberField(TEXT("selectedShapeCount"),Eligible);
    Result->SetBoolField(TEXT("staticSingleBodyPolicySupported"),StaticPolicy);
    Result->SetArrayField(TEXT("shapes"),Rows);Result->SetBoolField(TEXT("complete"),Locked && Complete && Eligible>0);
    Result->SetStringField(TEXT("separationPolicy"),TEXT("diagnostic_only_static_single_body_rigid_unit_zero_margin_triangles_v1"));
    Result->SetBoolField(TEXT("separatedContactDiagnostic"),Locked && Complete && Eligible>0 && StaticPolicy && !MtdBlocking && Separated);
    Result->SetBoolField(TEXT("admissionGranted"),false);
    if (Contact)
    {
        Contact->ReadLockEntered=Locked;Contact->Complete=Locked && Complete && Eligible>0;
        Contact->MtdBlocking=MtdBlocking;Contact->StaticPolicySupported=StaticPolicy;Contact->SelectedShapes=Eligible;
        Contact->Decision=Locked && MtdBlocking ? EContactDecision::Blocked
            : Contact->Complete && StaticPolicy && !MtdBlocking && Separated ? EContactDecision::Separated : EContactDecision::Unresolved;
    }
    return Result;
}

WarCitadelCookedContacts::FSceneContact WarCitadelCookedContacts::ResolveOverlaps(
    const TArray<FOverlapResult>& Hits,const FVector& Center,const FQuat& Rotation,double Radius,double HalfHeight,bool TraceComplex)
{
    FSceneContact Result;Result.Diagnostic=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Rows;
    TMap<TPair<const UPrimitiveComponent*,int32>,int32> Seen;
    TArray<const FBodyInstance*> SeenBodies;TArray<Chaos::FPhysicsObjectHandle> SeenObjects;
    TArray<EContactDecision> Decisions;int32 InconsistentDuplicates=0;
    const bool ValidCapsule=!Center.ContainsNaN() && !Rotation.ContainsNaN() && Rotation.IsNormalized()
        && FMath::IsFinite(Radius) && FMath::IsFinite(HalfHeight) && Radius>0 && HalfHeight>=Radius;
    for (const auto& Hit:Hits)
    {
        if (!Hit.bBlockingHit) continue;
        ++Result.RawBlockingHits;
        const auto* Component=Hit.GetComponent();const int32 Item=Hit.GetItemIndex();
        // Inspect the original child body. Asking for a welded parent here would
        // erase the overlap identity before the nonwelded policy is enforced.
        const auto* Body=Component ? Component->GetBodyInstance(NAME_None,false,Item) : nullptr;
        bool Binding=ValidCapsule && IsInGameThread() && Component && Body && Item==INDEX_NONE && !Body->WeldParent
            && Body->OwnerComponent.Get()==Component && Body->InstanceBodyIndex==INDEX_NONE
            && (!Hit.PhysicsObject || Hit.PhysicsObject==Component->GetPhysicsObjectByName(NAME_None));
        if (Component)
        {
            if (const int32* Existing=Seen.Find({Component,Item}))
            {
                if (!Binding || SeenBodies[*Existing]!=Body || SeenObjects[*Existing]!=Hit.PhysicsObject)
                {
                    ++InconsistentDuplicates;
                    Rows[*Existing]->AsObject()->SetBoolField(TEXT("inconsistentDuplicateBinding"),true);
                    if (Decisions[*Existing]==EContactDecision::Separated)
                    {
                        --Result.SeparatedBodies;++Result.UnresolvedBodies;Decisions[*Existing]=EContactDecision::Unresolved;
                        Rows[*Existing]->AsObject()->SetStringField(TEXT("decision"),TEXT("unresolved"));
                    }
                }
                continue;
            }
            Seen.Add({Component,Item},Rows.Num());
        }
        ++Result.UniqueBodies;
        auto Row=MakeShared<FJsonObject>();FBodyContact Contact;
        Row->SetStringField(TEXT("component"),Component ? Component->GetPathName() : TEXT(""));
        Row->SetNumberField(TEXT("overlapItemIndex"),Item);
        if (Binding)
        {
            const FTransform Before=Component->GetComponentTransform();
            Row->SetObjectField(TEXT("liveWitness"),Witness(Body,Center,Rotation,Radius,HalfHeight,TraceComplex,&Contact));
            Binding=Component->GetBodyInstance(NAME_None,false,Item)==Body && !Body->WeldParent
                && Body->OwnerComponent.Get()==Component && Component->GetComponentTransform().Equals(Before,1.e-10);
        }
        if (!Binding) Contact.Decision=EContactDecision::Unresolved;
        Row->SetBoolField(TEXT("originalBodyBindingVerified"),Binding);
        if (Contact.Decision==EContactDecision::Separated) { ++Result.SeparatedBodies;Row->SetStringField(TEXT("decision"),TEXT("separated")); }
        else if (Contact.Decision==EContactDecision::Blocked) { ++Result.BlockedBodies;Row->SetStringField(TEXT("decision"),TEXT("blocked")); }
        else { ++Result.UnresolvedBodies;Row->SetStringField(TEXT("decision"),TEXT("unresolved")); }
        Rows.Add(MakeShared<FJsonValueObject>(Row));
        SeenBodies.Add(Body);SeenObjects.Add(Hit.PhysicsObject);Decisions.Add(Contact.Decision);
    }
    Result.Decision=!ValidCapsule ? EContactDecision::Unresolved : Result.RawBlockingHits==0 ? EContactDecision::RawClear
        : Result.BlockedBodies>0 ? EContactDecision::Blocked
        : Result.UnresolvedBodies>0 || InconsistentDuplicates>0 ? EContactDecision::Unresolved : EContactDecision::Separated;
    Result.Diagnostic->SetBoolField(TEXT("capsuleInputValid"),ValidCapsule);
    Result.Diagnostic->SetNumberField(TEXT("inconsistentDuplicateCount"),InconsistentDuplicates);
    Result.Diagnostic->SetNumberField(TEXT("rawBlockingHitCount"),Result.RawBlockingHits);
    Result.Diagnostic->SetNumberField(TEXT("uniqueBlockingBodyCount"),Result.UniqueBodies);
    Result.Diagnostic->SetNumberField(TEXT("resolvedSeparatedBodyCount"),Result.SeparatedBodies);
    Result.Diagnostic->SetNumberField(TEXT("blockedBodyCount"),Result.BlockedBodies);
    Result.Diagnostic->SetNumberField(TEXT("unresolvedBodyCount"),Result.UnresolvedBodies);
    Result.Diagnostic->SetArrayField(TEXT("perBodyDecisions"),Rows);
    Result.Diagnostic->SetStringField(TEXT("proposalDecision"),Result.Decision==EContactDecision::RawClear ? TEXT("raw_clear")
        : Result.Decision==EContactDecision::Separated ? TEXT("all_raw_contacts_proven_separated")
        : Result.Decision==EContactDecision::Blocked ? TEXT("blocked") : TEXT("unresolved"));
    Result.Diagnostic->SetBoolField(TEXT("diagnosticOnly"),true);Result.Diagnostic->SetBoolField(TEXT("admissionGranted"),false);
    return Result;
}
