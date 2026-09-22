#pragma once
#include "Brushes/SlateDynamicImageBrush.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"
#include "WarAbilityBarLayout.h"
#include "Widgets/SCompoundWidget.h"
#include "Rendering/DrawElements.h"

/** Original PNGs stay unchanged. UV regions exclude their transparent export margins. */
namespace WarUiArtwork
{
    inline TSharedRef<FSlateDynamicImageBrush> Image(const TCHAR* File, FVector2D Size)
    {
        return MakeShared<FSlateDynamicImageBrush>(FName(*FPaths::Combine(FPaths::ProjectContentDir(), TEXT("UI"), File)), Size);
    }
}

/** Normalize the painted inner square, not the complete endcap image. Ornaments live outside the hit box. */
class SWarAbilityCell : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarAbilityCell) {} SLATE_ARGUMENT(int32,Index) SLATE_ARGUMENT(int32,Count)
        SLATE_DEFAULT_SLOT(FArguments,Content) SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        Art = WarAbilityBarLayout::Artwork(Args._Index,Args._Count);
        Texture = WarUiArtwork::Image(Art.File,Art.SourceSize);
        Brush = *Texture;
        Brush.SetUVRegion(FBox2D(Art.Visible.Min/Art.SourceSize,Art.Visible.Max/Art.SourceSize));
        ChildSlot[Args._Content.Widget];
    }
    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& Cull,
        FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const override
    {
        const FVector2D Size = Geometry.GetLocalSize();
        const FVector2D Scale(Size.Y/Art.Inner.GetSize().X,Size.Y/Art.Inner.GetSize().Y);
        const FVector2D Origin((Size.X-Size.Y)/2,0);
        const FVector2D Offset = Origin+(Art.Visible.Min-Art.Inner.Min)*Scale;
        const FLinearColor Tint = Style.GetColorAndOpacityTint()*(IsHovered() ? FLinearColor(1.15f,1.1f,1.f) : FLinearColor::White);
        FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(Art.Visible.GetSize()*Scale,
            FSlateLayoutTransform(Offset)),&Brush,ESlateDrawEffect::None,Tint);
        return SCompoundWidget::OnPaint(Args,Geometry,Cull,Elements,Layer+1,Style,Enabled);
    }
private:
    WarAbilityBarLayout::FArtwork Art;
    TSharedPtr<FSlateDynamicImageBrush> Texture;
    FSlateBrush Brush;
};

/** Nine-sliced tall window: fixed ornamental corners with an extensible stone interior. */
class SWarArtWindow : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarArtWindow) {} SLATE_DEFAULT_SLOT(FArguments,Content) SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        Texture = WarUiArtwork::Image(TEXT("window.png"), FVector2D(1086,1448));
        const double X[] = {63,210,878,1023}, Y[] = {14,240,1250,1410};
        for (int32 Row=0;Row<3;++Row) for (int32 Column=0;Column<3;++Column)
        {
            FSlateBrush Brush = *Texture;
            Brush.SetUVRegion(FBox2D(FVector2D(X[Column]/1086,Y[Row]/1448),FVector2D(X[Column+1]/1086,Y[Row+1]/1448)));
            Slices.Add(Brush);
        }
        ChildSlot.Padding(FMargin(30,50,30,36))[Args._Content.Widget];
    }
    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& Cull,
        FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const override
    {
        const FVector2D Size = Geometry.GetLocalSize();
        const double Scale = FMath::Min(1.,FMath::Min(Size.X/100.,Size.Y/140.));
        const double X[] = {0,40*Scale,Size.X-40*Scale,Size.X}, Y[] = {0,62*Scale,Size.Y-44*Scale,Size.Y};
        for (int32 Row=0;Row<3;++Row) for (int32 Column=0;Column<3;++Column)
            FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(FVector2D(X[Column+1]-X[Column],Y[Row+1]-Y[Row]),
                FSlateLayoutTransform(FVector2D(X[Column],Y[Row]))),&Slices[Row*3+Column],ESlateDrawEffect::None,Style.GetColorAndOpacityTint());
        return SCompoundWidget::OnPaint(Args,Geometry,Cull,Elements,Layer+1,Style,Enabled);
    }
private:
    TSharedPtr<FSlateDynamicImageBrush> Texture;
    TArray<FSlateBrush> Slices;
};
